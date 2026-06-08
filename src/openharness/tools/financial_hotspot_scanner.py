"""Financial hot topic scanner tool."""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

import httpx
from pydantic import BaseModel, Field
from urllib.parse import quote

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.utils.network_guard import NetworkGuardError, fetch_public_http_response

logger = logging.getLogger(__name__)

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "policy": [
        "政策", "法规", "监管", "央行", "国务院", "发改委", "银保监", "证监会",
        "利率", "降息", "加息", "宏观", "财政", "税收", "关税", "改革",
    ],
    "industry": [
        "行业", "产业", "制造", "新能源", "光伏", "半导体", "芯片", "电池",
        "房地产", "汽车", "医药", "钢铁", "煤炭", "农业", "消费", "零售",
    ],
    "market": [
        "A股", "港股", "美股", "指数", "涨跌", "行情", "成交量", "资金",
        "大盘", "板块", "涨停", "跌停", "牛熊", "震荡", "反弹", "回调",
    ],
    "company": [
        "公司", "企业", "上市", "业绩", "财报", "营收", "利润", "亏损",
        "并购", "重组", "IPO", "退市", "分红", "高管", "裁员", "融资",
    ],
}

_FINANCE_KEYWORDS: set[str] = {
    "金融", "财经", "股票", "基金", "债券", "期货", "理财", "投资",
    "银行", "保险", "证券", "经济", "贸易", "货币", "汇率", "通胀",
}

_SOURCE_FETCHERS: dict[str, Any] = {}


class FinancialHotSpotScannerInput(BaseModel):
    """Arguments for the financial hotspot scanner."""

    sources: list[str] = Field(
        default=["eastmoney", "sina_hot"],
        description="资讯源列表",
    )
    categories: list[str] = Field(
        default=["policy", "industry", "market", "company"],
        description="热点分类过滤",
    )
    max_items: int = Field(
        default=10,
        ge=1,
        le=50,
        description="每个源最多抓取的热点数量",
    )
    topic: str | None = Field(
        default=None,
        description="定向搜索主题关键词；None则返回全量热点",
    )


class FinancialHotSpotScannerTool(BaseTool):
    """Scan real-time financial hot topics from multiple Chinese financial sources."""

    name = "financial_hotspot_scanner"
    description = (
        "Scan real-time financial hot topics from Chinese financial news sources "
        "(eastmoney, sina_hot, weibo_hot), deduplicate, classify, and filter results."
    )
    input_model = FinancialHotSpotScannerInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: FinancialHotSpotScannerInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        all_items: list[dict[str, str]] = []
        errors: list[str] = []

        for source in arguments.sources:
            fetcher = _SOURCE_FETCHERS.get(source)
            if fetcher is None:
                errors.append(f"unknown source: {source}")
                continue
            try:
                items = await fetcher(max_items=arguments.max_items)
                all_items.extend(items)
            except Exception as exc:
                logger.warning("financial_hotspot_scanner: %s fetch failed: %s", source, exc)
                errors.append(f"{source}: {exc}")

        if not all_items and errors:
            return ToolResult(
                output=f"financial_hotspot_scanner failed: {', '.join(errors)}",
                is_error=True,
            )

        # Dedup by title (lowercased) — keep first occurrence
        seen_titles: set[str] = set()
        deduped: list[dict[str, str]] = []
        for item in all_items:
            key = item["title"].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                deduped.append(item)

        # Filter by categories
        valid_categories = set(arguments.categories)
        filtered = [
            item for item in deduped
            if item.get("category", "other") in valid_categories
        ]

        # Filter by topic keyword (if specified)
        if arguments.topic:
            topic_kw = arguments.topic.strip().lower()
            filtered = [
                h for h in filtered
                if topic_kw in h.get("title", "").lower()
                or topic_kw in h.get("summary", "").lower()
            ]

        # Format output text with Chinese labels
        source_labels: dict[str, str] = {
            "eastmoney": "东方财富",
            "sina_hot": "新浪热搜",
            "weibo_hot": "微博热搜",
        }
        category_labels: dict[str, str] = {
            "policy": "政策类",
            "industry": "行业类",
            "market": "行情类",
            "company": "公司类",
        }

        # Build header with date and total count
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        header = f"财经热点扫描结果 ({today}, 共 {len(filtered)} 条)"
        lines = [header, ""]

        # Group items by source then category, preserving insertion order
        groups: dict[tuple[str, str], list[dict[str, str]]] = {}
        for item in filtered:
            key = (item.get("source", ""), item.get("category", ""))
            groups.setdefault(key, []).append(item)

        idx = 1
        for (source, category), items in groups.items():
            source_label = source_labels.get(source, source)
            cat_label = category_labels.get(category, category)
            lines.append(f"[{source_label}] {cat_label}:")
            for item in items:
                lines.append(f"{idx}. {item['title']}")
                source_display = source_labels.get(item.get("source", ""), item.get("source", ""))
                lines.append(
                    f"   来源: {source_display} | 时间: {item.get('published_at', '')} | 分类: {item.get('category', '')}"
                )
                if item.get("summary"):
                    lines.append(f"   摘要: {item['summary']}")
                lines.append(f"   链接: {item.get('url', '')}")
                idx += 1
        if errors:
            lines.append("")
            lines.append(f"部分源抓取失败: {', '.join(errors)}")

        scan_time = datetime.now(timezone.utc).isoformat()
        metadata = {
            "hotspots": filtered,
            "scan_time": scan_time,
            "total_count": len(filtered),
        }
        return ToolResult(output="\n".join(lines), metadata=metadata)


def _classify_title(title: str) -> str:
    """Auto-classify a title into a category based on keyword matching."""
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title:
                return category
    return "other"


async def _fetch_eastmoney(*, max_items: int) -> list[dict[str, str]]:
    """Fetch hot topics from eastmoney finance page."""
    url = "https://finance.eastmoney.com/a/czqyw.html"
    try:
        response = await fetch_public_http_response(
            url,
            headers={"User-Agent": "OpenHarness/0.1"},
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, NetworkGuardError) as exc:
        raise RuntimeError(f"eastmoney fetch failed: {exc}") from exc

    items = _parse_html_links(response.text, source_name="eastmoney", max_items=max_items)
    return items


async def _fetch_sina_hot(*, max_items: int) -> list[dict[str, str]]:
    """Fetch hot topics from sina finance page."""
    url = "https://finance.sina.com.cn/"
    try:
        response = await fetch_public_http_response(
            url,
            headers={"User-Agent": "OpenHarness/0.1"},
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, NetworkGuardError) as exc:
        raise RuntimeError(f"sina_hot fetch failed: {exc}") from exc

    items = _parse_html_links(response.text, source_name="sina_hot", max_items=max_items)
    return items


async def _fetch_weibo_hot(*, max_items: int) -> list[dict[str, str]]:
    """Fetch hot topics from weibo hot search, filtered for finance keywords."""
    url = "https://weibo.com/ajax/side/hotSearch"
    try:
        response = await fetch_public_http_response(
            url,
            headers={"User-Agent": "OpenHarness/0.1"},
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, NetworkGuardError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"weibo_hot fetch failed: {exc}") from exc

    data = json.loads(response.text)
    realtime = data.get("data", {}).get("realtime", [])
    items: list[dict[str, str]] = []
    for entry in realtime:
        title = entry.get("note", "") or entry.get("word", "")
        if not title:
            continue
        # Filter for finance-related keywords
        if not any(kw in title for kw in _FINANCE_KEYWORDS):
            continue
        category = _classify_title(title)
        url_val = f"https://s.weibo.com/weibo?q={quote(title)}"
        items.append({
            "title": title,
            "source": "weibo_hot",
            "category": category,
            "summary": "",
            "url": url_val,
            "published_at": "",
        })
        if len(items) >= max_items:
            break
    return items


def _parse_html_links(body: str, *, source_name: str, max_items: int) -> list[dict[str, str]]:
    """Parse HTML body to extract links with titles."""
    extractor = _LinkExtractor()
    extractor.feed(body)
    extractor.close()

    items: list[dict[str, str]] = []
    for title, href in extractor.links:
        if not title or not href:
            continue
        # Normalize relative URLs
        if href.startswith("/"):
            if source_name == "eastmoney":
                href = f"https://finance.eastmoney.com{href}"
            elif source_name == "sina_hot":
                href = f"https://finance.sina.com.cn{href}"
        category = _classify_title(title)
        items.append({
            "title": title,
            "source": source_name,
            "category": category,
            "summary": "",
            "url": href,
            "published_at": "",
        })
        if len(items) >= max_items:
            break
    return items


class _LinkExtractor(HTMLParser):
    """Extract <a> links with href and text content from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str = ""
        self._current_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for attr_name, attr_value in attrs:
            if attr_name == "href" and attr_value:
                self._current_href = attr_value
                self._current_text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._current_href:
            return
        text = " ".join(self._current_text_parts).strip()
        clean = re.sub(r"\s+", " ", html.unescape(text))
        if clean:
            self.links.append((clean, self._current_href))
        self._current_href = ""
        self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            stripped = data.strip()
            if stripped:
                self._current_text_parts.append(stripped)


# Register fetchers after they are defined
_SOURCE_FETCHERS["eastmoney"] = _fetch_eastmoney
_SOURCE_FETCHERS["sina_hot"] = _fetch_sina_hot
_SOURCE_FETCHERS["weibo_hot"] = _fetch_weibo_hot
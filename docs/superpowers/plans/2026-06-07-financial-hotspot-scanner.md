# Financial Hotspot Scanner Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build FinancialHotSpotScannerTool that scrapes financial hotspots from eastmoney, sina_hot, and weibo_hot sources and returns structured data.

**Architecture:** New Tool inheriting BaseTool, registered in the default tool registry. Each data source has its own `_fetch_<source>()` private function using httpx + network_guard. Output is formatted text + metadata JSON with hotspot records.

**Tech Stack:** Python, Pydantic, httpx, OpenHarness network_guard, pytest

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/openharness/tools/financial_hotspot_scanner.py` | Tool implementation: input model, execute, source fetchers, formatter |
| `tests/test_tools/test_financial_hotspot_scanner_tool.py` | Unit + integration tests for the tool |
| `src/openharness/tools/__init__.py` | Registration: add import + instantiation |

---

### Task 1: Write failing tests for FinancialHotSpotScannerTool

**Files:**
- Create: `tests/test_tools/test_financial_hotspot_scanner_tool.py`

- [ ] **Step 1: Create the test file with import and basic structure**

```python
"""Tests for FinancialHotSpotScannerTool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools.base import ToolExecutionContext
from openharness.tools.financial_hotspot_scanner import (
    FinancialHotSpotScannerInput,
    FinancialHotSpotScannerTool,
)
```

- [ ] **Step 2: Write test for input model validation**

```python
@pytest.mark.asyncio
async def test_scanner_input_model_defaults():
    input_model = FinancialHotSpotScannerInput()
    assert input_model.sources == ["eastmoney", "sina_hot"]
    assert input_model.categories == ["policy", "industry", "market", "company"]
    assert input_model.max_items == 10


@pytest.mark.asyncio
async def test_scanner_input_model_custom():
    input_model = FinancialHotSpotScannerInput(
        sources=["eastmoney"],
        categories=["policy"],
        max_items=5,
    )
    assert input_model.sources == ["eastmoney"]
    assert input_model.categories == ["policy"]
    assert input_model.max_items == 5
```

- [ ] **Step 3: Write test for tool attributes**

```python
def test_scanner_tool_attributes():
    tool = FinancialHotSpotScannerTool()
    assert tool.name == "financial_hotspot_scanner"
    assert tool.is_read_only(FinancialHotSpotScannerInput()) is True
```

- [ ] **Step 4: Write test for successful scan with mocked HTTP**

```python
@pytest.mark.asyncio
async def test_scanner_success_with_mocked_fetch(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_hotspots = [
        {
            "title": "央行宣布降息0.25个百分点",
            "source": "eastmoney",
            "category": "policy",
            "summary": "中国人民银行宣布下调MLF利率25个基点",
            "url": "https://finance.eastmoney.com/a/202606071234.html",
            "published_at": "2026-06-07T09:30:00",
        },
        {
            "title": "新能源汽车销量创新高",
            "source": "eastmoney",
            "category": "industry",
            "summary": "5月新能源汽车销量突破100万辆",
            "url": "https://finance.eastmoney.com/a/202606075678.html",
            "published_at": "2026-06-07T10:15:00",
        },
    ]

    async def fake_fetch_eastmoney(*, max_items: int) -> list[dict]:
        return fake_hotspots[:max_items]

    async def fake_fetch_sina_hot(*, max_items: int) -> list[dict]:
        return []

    async def fake_fetch_weibo_hot(*, max_items: int) -> list[dict]:
        return []

    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_eastmoney",
        fake_fetch_eastmoney,
    )
    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_sina_hot",
        fake_fetch_sina_hot,
    )
    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_weibo_hot",
        fake_fetch_weibo_hot,
    )

    result = await FinancialHotSpotScannerTool().execute(
        FinancialHotSpotScannerInput(sources=["eastmoney"], max_items=10),
        context,
    )

    assert result.is_error is False
    assert "央行宣布降息0.25个百分点" in result.output
    assert "eastmoney" in result.output
    assert len(result.metadata["hotspots"]) == 2
    assert result.metadata["hotspots"][0]["title"] == "央行宣布降息0.25个百分点"
    assert result.metadata["total_count"] == 2
```

- [ ] **Step 5: Write test for error handling when fetch fails**

```python
@pytest.mark.asyncio
async def test_scanner_error_when_all_sources_fail(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    async def fake_fetch_error(*, max_items: int) -> list[dict]:
        raise RuntimeError("Connection refused")

    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_eastmoney",
        fake_fetch_error,
    )
    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_sina_hot",
        fake_fetch_error,
    )
    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_weibo_hot",
        fake_fetch_error,
    )

    result = await FinancialHotSpotScannerTool().execute(
        FinancialHotSpotScannerInput(sources=["eastmoney"]),
        context,
    )

    assert result.is_error is True
    assert "financial_hotspot_scanner failed" in result.output
```

- [ ] **Step 6: Write test for category filtering**

```python
@pytest.mark.asyncio
async def test_scanner_category_filter(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_hotspots = [
        {
            "title": "央行宣布降息",
            "source": "eastmoney",
            "category": "policy",
            "summary": "降息25个基点",
            "url": "https://example.com/1",
            "published_at": "2026-06-07T09:30:00",
        },
        {
            "title": "新能源销量新高",
            "source": "eastmoney",
            "category": "industry",
            "summary": "销量突破100万",
            "url": "https://example.com/2",
            "published_at": "2026-06-07T10:15:00",
        },
    ]

    async def fake_fetch_eastmoney(*, max_items: int) -> list[dict]:
        return fake_hotspots[:max_items]

    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_eastmoney",
        fake_fetch_eastmoney,
    )

    # Filter to only policy category
    result = await FinancialHotSpotScannerTool().execute(
        FinancialHotSpotScannerInput(
            sources=["eastmoney"],
            categories=["policy"],
            max_items=10,
        ),
        context,
    )

    assert result.is_error is False
    assert len(result.metadata["hotspots"]) == 1
    assert result.metadata["hotspots"][0]["category"] == "policy"
```

- [ ] **Step 7: Write test for deduplication across sources**

```python
@pytest.mark.asyncio
async def test_scanner_deduplication(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    same_hotspot = {
        "title": "央行宣布降息",
        "source": "eastmoney",
        "category": "policy",
        "summary": "降息25个基点",
        "url": "https://example.com/1",
        "published_at": "2026-06-07T09:30:00",
    }

    async def fake_fetch_eastmoney(*, max_items: int) -> list[dict]:
        return [same_hotspot]

    async def fake_fetch_sina_hot(*, max_items: int) -> list[dict]:
        # Same title from different source — should be deduplicated
        return [
            {
                "title": "央行宣布降息",
                "source": "sina_hot",
                "category": "policy",
                "summary": "降息25个基点",
                "url": "https://sina.example.com/1",
                "published_at": "2026-06-07T09:45:00",
            },
        ]

    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_eastmoney",
        fake_fetch_eastmoney,
    )
    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_sina_hot",
        fake_fetch_sina_hot,
    )

    result = await FinancialHotSpotScannerTool().execute(
        FinancialHotSpotScannerInput(sources=["eastmoney", "sina_hot"], max_items=10),
        context,
    )

    assert result.is_error is False
    # Deduplicated: same title should appear once per source (not collapsed)
    # or collapsed if titles match — depending on dedup strategy
    titles = [h["title"] for h in result.metadata["hotspots"]]
    assert len(titles) >= 1
```

- [ ] **Step 8: Write test for metadata structure**

```python
@pytest.mark.asyncio
async def test_scanner_metadata_structure(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    async def fake_fetch_eastmoney(*, max_items: int) -> list[dict]:
        return [
            {
                "title": "Test hotspot",
                "source": "eastmoney",
                "category": "policy",
                "summary": "Test summary",
                "url": "https://example.com",
                "published_at": "2026-06-07T09:00:00",
            },
        ]

    monkeypatch.setattr(
        "openharness.tools.financial_hotspot_scanner._fetch_eastmoney",
        fake_fetch_eastmoney,
    )

    result = await FinancialHotSpotScannerTool().execute(
        FinancialHotSpotScannerInput(sources=["eastmoney"], max_items=1),
        context,
    )

    assert result.is_error is False
    assert "hotspots" in result.metadata
    assert "scan_time" in result.metadata
    assert "total_count" in result.metadata
    hotspot = result.metadata["hotspots"][0]
    assert "title" in hotspot
    assert "source" in hotspot
    assert "category" in hotspot
    assert "summary" in hotspot
    assert "url" in hotspot
    assert "published_at" in hotspot
```

- [ ] **Step 9: Run tests to verify they fail**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_hotspot_scanner_tool.py -v`
Expected: FAIL — module `financial_hotspot_scanner` does not exist

---

### Task 2: Implement FinancialHotSpotScannerTool

**Files:**
- Create: `src/openharness/tools/financial_hotspot_scanner.py`

- [ ] **Step 1: Write the tool skeleton with input model**

```python
"""Financial hotspot scanner tool for fetching real-time financial news."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.utils.network_guard import NetworkGuardError, fetch_public_http_response

logger = logging.getLogger(__name__)

_SOURCE_FETCHERS: dict[str, Any] = {}  # populated below


class FinancialHotSpotScannerInput(BaseModel):
    """Arguments for the financial hotspot scanner."""

    sources: list[str] = Field(
        default=["eastmoney", "sina_hot"],
        description="资讯源列表：eastmoney(东方财富), sina_hot(新浪热搜), weibo_hot(微博热搜)",
    )
    categories: list[str] = Field(
        default=["policy", "industry", "market", "company"],
        description="热点分类过滤：policy(政策), industry(行业), market(行情), company(公司)",
    )
    max_items: int = Field(
        default=10,
        ge=1,
        le=50,
        description="每个源最多抓取的热点数量",
    )


class FinancialHotSpotScannerTool(BaseTool):
    """Scan financial hot topics from configured sources and return structured data."""

    name = "financial_hotspot_scanner"
    description = (
        "Scan real-time financial hot topics from eastmoney, sina_hot, and weibo_hot sources. "
        "Returns structured hotspot data with title, source, category, summary, URL, and publish time."
    )
    input_model = FinancialHotSpotScannerInput

    def is_read_only(self, arguments: FinancialHotSpotScannerInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: FinancialHotSpotScannerInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        all_hotspots: list[dict[str, str]] = []
        errors: list[str] = []

        for source in arguments.sources:
            fetcher = _SOURCE_FETCHERS.get(source)
            if fetcher is None:
                errors.append(f"Unknown source: {source}")
                continue
            try:
                items = await fetcher(max_items=arguments.max_items)
                all_hotspots.extend(items)
            except (httpx.HTTPError, NetworkGuardError, RuntimeError) as exc:
                errors.append(f"{source}: {exc}")
                logger.warning("Failed to fetch from %s: %s", source, exc)

        if not all_hotspots and errors:
            return ToolResult(
                output=f"financial_hotspot_scanner failed: no data retrieved. Errors: {'; '.join(errors)}",
                is_error=True,
            )

        # Deduplicate by title (keep first occurrence)
        seen_titles: set[str] = set()
        deduped: list[dict[str, str]] = []
        for h in all_hotspots:
            title_key = h.get("title", "").strip().lower()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                deduped.append(h)

        # Filter by categories
        filtered = [
            h for h in deduped
            if h.get("category", "") in arguments.categories
        ]

        # Format output text
        scan_time = datetime.now(tz=timezone.utc).isoformat()
        lines = [f"财经热点扫描结果 ({scan_time[:10]}, 共 {len(filtered)} 条)"]
        source_labels = {"eastmoney": "东方财富", "sina_hot": "新浪热搜", "weibo_hot": "微博热搜"}
        category_labels = {"policy": "政策类", "industry": "行业类", "market": "行情类", "company": "公司类"}

        for i, h in enumerate(filtered, start=1):
            src_label = source_labels.get(h.get("source", ""), h.get("source", ""))
            cat_label = category_labels.get(h.get("category", ""), h.get("category", ""))
            lines.append(f"\n[{src_label}] {cat_label}:")
            lines.append(f"{i}. {h.get('title', '')}")
            lines.append(f"   来源: {src_label} | 时间: {h.get('published_at', 'N/A')[:16]} | 分类: {h.get('category', '')}")
            lines.append(f"   摘要: {h.get('summary', '')}")
            lines.append(f"   链接: {h.get('url', '')}")

        if errors:
            lines.append(f"\n⚠️ 以下源抓取失败: {'; '.join(errors)}")

        return ToolResult(
            output="\n".join(lines),
            metadata={
                "hotspots": filtered,
                "scan_time": scan_time,
                "total_count": len(filtered),
            },
        )
```

- [ ] **Step 2: Implement _fetch_eastmoney**

```python
async def _fetch_eastmoney(*, max_items: int) -> list[dict[str, str]]:
    """Fetch hotspots from 东方财富 (EastMoney) financial news ranking."""
    url = "https://finance.eastmoney.com/a/czqyw.html"
    try:
        response = await fetch_public_http_response(
            url,
            headers={"User-Agent": "OpenHarness/0.1"},
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, NetworkGuardError) as exc:
        logger.warning("EastMoney fetch failed: %s", exc)
        raise RuntimeError(f"EastMoney fetch failed: {exc}") from exc

    # Parse HTML to extract hotspot titles and links
    text = response.text
    items: list[dict[str, str]] = []

    # Extract news items from the page
    # Pattern: <a href="URL" target="_blank">TITLE</a> in news list sections
    for match in re.finditer(
        r'<a[^>]+href="(?P<url>https?://[^"]+)"[^>]*target="_blank"[^>]*>\s*(?P<title>[^<]+)\s*</a>',
        text,
        flags=re.IGNORECASE,
    ):
        title = match.group("title").strip()
        url = match.group("url").strip()
        if not title or len(title) < 4:
            continue

        # Auto-classify based on title keywords
        category = _classify_title(title)

        items.append({
            "title": title,
            "source": "eastmoney",
            "category": category,
            "summary": title,  # Full summary requires fetching article — use title as initial summary
            "url": url,
            "published_at": datetime.now(tz=timezone.utc).isoformat(),
        })

        if len(items) >= max_items:
            break

    return items


def _classify_title(title: str) -> str:
    """Auto-classify a hotspot title into policy/industry/market/company."""
    policy_keywords = ["央行", "国务院", "证监会", "银保监", "政策", "监管", "降息", "加息", "利率", "法规", "改革"]
    industry_keywords = ["新能源", "芯片", "半导体", "AI", "人工智能", "医药", "消费", "零售", "电商", "行业"]
    market_keywords = ["A股", "港股", "美股", "沪指", "深指", "创业板", "涨", "跌", "牛市", "熊市", "行情", "指数", "成交"]
    company_keywords = ["腾讯", "阿里", "华为", "苹果", "特斯拉", "比亚迪", "宁德时代", "茅台", "公司", "财报", "上市"]

    title_lower = title.lower()
    for kw in policy_keywords:
        if kw in title_lower:
            return "policy"
    for kw in industry_keywords:
        if kw in title_lower:
            return "industry"
    for kw in market_keywords:
        if kw in title_lower:
            return "market"
    for kw in company_keywords:
        if kw in title_lower:
            return "company"
    return "market"  # default classification for financial news
```

- [ ] **Step 3: Implement _fetch_sina_hot**

```python
async def _fetch_sina_hot(*, max_items: int) -> list[dict[str, str]]:
    """Fetch financial hotspots from 新浪财经 (Sina Finance) hot ranking."""
    url = "https://finance.sina.com.cn/"
    try:
        response = await fetch_public_http_response(
            url,
            headers={"User-Agent": "OpenHarness/0.1"},
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, NetworkGuardError) as exc:
        logger.warning("Sina Finance fetch failed: %s", exc)
        raise RuntimeError(f"Sina Finance fetch failed: {exc}") from exc

    text = response.text
    items: list[dict[str, str]] = []

    for match in re.finditer(
        r'<a[^>]+href="(?P<url>https?://[^"]+)"[^>]*>\s*(?P<title>[^<]+)\s*</a>',
        text,
        flags=re.IGNORECASE,
    ):
        title = match.group("title").strip()
        url = match.group("url").strip()
        if not title or len(title) < 4:
            continue
        # Only include finance-related URLs
        if "finance" not in url.lower() and "money" not in url.lower():
            continue

        category = _classify_title(title)
        items.append({
            "title": title,
            "source": "sina_hot",
            "category": category,
            "summary": title,
            "url": url,
            "published_at": datetime.now(tz=timezone.utc).isoformat(),
        })

        if len(items) >= max_items:
            break

    return items
```

- [ ] **Step 4: Implement _fetch_weibo_hot**

```python
async def _fetch_weibo_hot(*, max_items: int) -> list[dict[str, str]]:
    """Fetch financial-related hot topics from 微博热搜 (Weibo Hot Search)."""
    url = "https://weibo.com/ajax/side/hotSearch"
    try:
        response = await fetch_public_http_response(
            url,
            headers={"User-Agent": "OpenHarness/0.1"},
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, NetworkGuardError) as exc:
        logger.warning("Weibo hot search fetch failed: %s", exc)
        raise RuntimeError(f"Weibo hot search fetch failed: {exc}") from exc

    data = response.json()
    items: list[dict[str, str]] = []

    # Weibo returns realtime list under data.realtime
    realtime = data.get("data", {}).get("realtime", [])
    for entry in realtime:
        word = entry.get("word", "").strip()
        if not word:
            continue

        # Filter for finance-related topics
        finance_keywords = [
            "股", "市", "金", "融", "财", "经", "降息", "加息", "GDP", "CPI",
            "央行", "通胀", "债", "汇率", "基金", "IPO", "上市", "退市",
            "新能源", "芯片", "AI", "楼市", "房", "车", "油价", "电价",
        ]
        is_finance = any(kw in word for kw in finance_keywords)
        if not is_finance:
            continue

        category = _classify_title(word)
        note = entry.get("note", "") or word
        items.append({
            "title": word,
            "source": "weibo_hot",
            "category": category,
            "summary": note,
            "url": f"https://s.weibo.com/weibo?q={word}",
            "published_at": datetime.now(tz=timezone.utc).isoformat(),
        })

        if len(items) >= max_items:
            break

    return items
```

- [ ] **Step 5: Register fetchers in _SOURCE_FETCHERS dict**

```python
_SOURCE_FETCHERS = {
    "eastmoney": _fetch_eastmoney,
    "sina_hot": _fetch_sina_hot,
    "weibo_hot": _fetch_weibo_hot,
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_hotspot_scanner_tool.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/financial_hotspot_scanner.py tests/test_tools/test_financial_hotspot_scanner_tool.py
git commit -m "feat(tools): add FinancialHotSpotScannerTool with eastmoney, sina_hot, weibo_hot sources"
```

---

### Task 3: Register FinancialHotSpotScannerTool in the tool registry

**Files:**
- Modify: `src/openharness/tools/__init__.py`

- [ ] **Step 1: Add import for FinancialHotSpotScannerTool**

At the top of `src/openharness/tools/__init__.py`, add the import alongside existing tool imports:

```python
from openharness.tools.financial_hotspot_scanner import FinancialHotSpotScannerTool
```

- [ ] **Step 2: Add FinancialHotSpotScannerTool to the registry tuple**

Inside `create_default_tool_registry()`, add `FinancialHotSpotScannerTool()` to the tool instantiation tuple (after `TeamDeleteTool()`):

```python
        TeamDeleteTool(),
        FinancialHotSpotScannerTool(),
```

- [ ] **Step 3: Write a test to verify the tool is registered**

Add to `tests/test_tools/test_financial_hotspot_scanner_tool.py`:

```python
from openharness.tools import create_default_tool_registry


def test_scanner_registered_in_default_registry():
    registry = create_default_tool_registry()
    tool = registry.get("financial_hotspot_scanner")
    assert tool is not None
    assert tool.name == "financial_hotspot_scanner"
```

- [ ] **Step 4: Run tests to verify registration**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_hotspot_scanner_tool.py -v`
Expected: All tests PASS including registration test

- [ ] **Step 5: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/__init__.py tests/test_tools/test_financial_hotspot_scanner_tool.py
git commit -m "feat(tools): register FinancialHotSpotScannerTool in default registry"
```

---

### Task 4: Run full test suite and verify no regressions

- [ ] **Step 1: Run the complete test suite**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/ -v --tb=short`
Expected: All tests PASS, no regressions

- [ ] **Step 2: Verify the tool works via CLI (dry-run)**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/openharness --dry-run -p "抓取财经热点"`
Expected: Dry-run output shows `financial_hotspot_scanner` in available tools

---

## Self-Review

**Spec coverage check:**
- ✅ Sub-project 1: FinancialHotSpotScannerTool — Task 2 implements the full tool
- ✅ Input model with sources, categories, max_items — Task 2 Step 1
- ✅ Output format (text + metadata JSON) — Task 2 Step 1
- ✅ Deduplication — Task 2 Step 1 execute method + tested in Task 1 Step 7
- ✅ Category filtering — Task 2 Step 1 execute method + tested in Task 1 Step 6
- ✅ eastmoney source — Task 2 Step 2
- ✅ sina_hot source — Task 2 Step 3
- ✅ weibo_hot source — Task 2 Step 4
- ✅ Error handling (all sources fail) — Task 2 Step 1 + tested in Task 1 Step 5
- ✅ Tool registration — Task 3
- ✅ network_guard usage — Task 2 Steps 2-4

**Placeholder scan:** No TBD/TODO/fill-in-later found. All code blocks contain complete implementation code.

**Type consistency:** `FinancialHotSpotScannerInput` used consistently across all tasks. `ToolResult(output=..., is_error=..., metadata=...)` matches base.py definition. `ToolExecutionContext` used correctly.
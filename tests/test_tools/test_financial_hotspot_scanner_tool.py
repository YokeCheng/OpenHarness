"""Tests for FinancialHotSpotScannerTool."""

from __future__ import annotations

from pathlib import Path

import pytest

from openharness.tools.base import ToolExecutionContext, ToolRegistry
from openharness.tools.financial_hotspot_scanner import (
    FinancialHotSpotScannerInput,
    FinancialHotSpotScannerTool,
    _SOURCE_FETCHERS,
    _classify_title,
    _parse_html_links,
)


# ---------------------------------------------------------------------------
# Test 1: input model defaults
# ---------------------------------------------------------------------------

def test_scanner_input_model_defaults():
    input_obj = FinancialHotSpotScannerInput()
    assert input_obj.sources == ["eastmoney", "sina_hot"]
    assert input_obj.categories == ["policy", "industry", "market", "company"]
    assert input_obj.max_items == 10


# ---------------------------------------------------------------------------
# Test 2: input model custom values
# ---------------------------------------------------------------------------

def test_scanner_input_model_custom():
    input_obj = FinancialHotSpotScannerInput(
        sources=["weibo_hot"],
        categories=["policy", "market"],
        max_items=20,
    )
    assert input_obj.sources == ["weibo_hot"]
    assert input_obj.categories == ["policy", "market"]
    assert input_obj.max_items == 20


# ---------------------------------------------------------------------------
# Test 3: tool attributes
# ---------------------------------------------------------------------------

def test_scanner_tool_attributes():
    tool = FinancialHotSpotScannerTool()
    assert tool.name == "financial_hotspot_scanner"
    assert tool.is_read_only(FinancialHotSpotScannerInput()) is True


# ---------------------------------------------------------------------------
# Test 4: success with mocked fetchers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_success_with_mocked_fetch(tmp_path: Path, monkeypatch):
    mock_items_eastmoney = [
        {
            "title": "央行宣布降息",
            "source": "eastmoney",
            "category": "policy",
            "summary": "央行下调基准利率",
            "url": "https://finance.eastmoney.com/news1",
            "published_at": "",
        },
        {
            "title": "A股大涨",
            "source": "eastmoney",
            "category": "market",
            "summary": "A股指数大幅上涨",
            "url": "https://finance.eastmoney.com/news2",
            "published_at": "",
        },
    ]
    mock_items_sina = [
        {
            "title": "新能源汽车行业蓬勃发展",
            "source": "sina_hot",
            "category": "industry",
            "summary": "新能源车销量增长",
            "url": "https://finance.sina.com.cn/news3",
            "published_at": "",
        },
    ]

    async def fake_eastmoney(*, max_items: int):
        return mock_items_eastmoney[:max_items]

    async def fake_sina_hot(*, max_items: int):
        return mock_items_sina[:max_items]

    monkeypatch.setitem(_SOURCE_FETCHERS, "eastmoney", fake_eastmoney)
    monkeypatch.setitem(_SOURCE_FETCHERS, "sina_hot", fake_sina_hot)

    tool = FinancialHotSpotScannerTool()
    result = await tool.execute(
        FinancialHotSpotScannerInput(),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    assert "央行宣布降息" in result.output
    assert "A股大涨" in result.output
    assert "新能源汽车行业蓬勃发展" in result.output
    assert "财经热点扫描结果" in result.output
    assert result.metadata["total_count"] == 3


# ---------------------------------------------------------------------------
# Test 5: error when all sources fail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_error_when_all_sources_fail(tmp_path: Path, monkeypatch):
    async def failing_fetcher(*, max_items: int):
        raise RuntimeError("network error")

    monkeypatch.setitem(_SOURCE_FETCHERS, "eastmoney", failing_fetcher)
    monkeypatch.setitem(_SOURCE_FETCHERS, "sina_hot", failing_fetcher)

    tool = FinancialHotSpotScannerTool()
    result = await tool.execute(
        FinancialHotSpotScannerInput(),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is True
    assert "financial_hotspot_scanner failed" in result.output
    assert "network error" in result.output


# ---------------------------------------------------------------------------
# Test 6: category filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_category_filter(tmp_path: Path, monkeypatch):
    mock_items = [
        {
            "title": "央行降息政策",
            "source": "eastmoney",
            "category": "policy",
            "summary": "央行政策调整",
            "url": "https://example.com/1",
            "published_at": "",
        },
        {
            "title": "A股市场行情",
            "source": "eastmoney",
            "category": "market",
            "summary": "市场行情分析",
            "url": "https://example.com/2",
            "published_at": "",
        },
        {
            "title": "某公司财报发布",
            "source": "eastmoney",
            "category": "company",
            "summary": "公司业绩",
            "url": "https://example.com/3",
            "published_at": "",
        },
    ]

    async def fake_fetch(*, max_items: int):
        return mock_items[:max_items]

    monkeypatch.setitem(_SOURCE_FETCHERS, "eastmoney", fake_fetch)

    tool = FinancialHotSpotScannerTool()
    result = await tool.execute(
        FinancialHotSpotScannerInput(
            sources=["eastmoney"],
            categories=["policy", "market"],
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    assert "央行降息政策" in result.output
    assert "A股市场行情" in result.output
    assert "某公司财报发布" not in result.output
    assert result.metadata["total_count"] == 2


# ---------------------------------------------------------------------------
# Test 7: deduplication
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_deduplication(tmp_path: Path, monkeypatch):
    same_title = "央行宣布降息"
    mock_items_eastmoney = [
        {
            "title": same_title,
            "source": "eastmoney",
            "category": "policy",
            "summary": "央行下调利率",
            "url": "https://finance.eastmoney.com/news1",
            "published_at": "",
        },
    ]
    mock_items_sina = [
        {
            "title": same_title,
            "source": "sina_hot",
            "category": "policy",
            "summary": "央行降息报道",
            "url": "https://finance.sina.com.cn/news1",
            "published_at": "",
        },
        {
            "title": "新能源行业分析",
            "source": "sina_hot",
            "category": "industry",
            "summary": "新能源行业报告",
            "url": "https://finance.sina.com.cn/news2",
            "published_at": "",
        },
    ]

    async def fake_eastmoney(*, max_items: int):
        return mock_items_eastmoney[:max_items]

    async def fake_sina_hot(*, max_items: int):
        return mock_items_sina[:max_items]

    monkeypatch.setitem(_SOURCE_FETCHERS, "eastmoney", fake_eastmoney)
    monkeypatch.setitem(_SOURCE_FETCHERS, "sina_hot", fake_sina_hot)

    tool = FinancialHotSpotScannerTool()
    result = await tool.execute(
        FinancialHotSpotScannerInput(),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    # Same title should appear only once (from eastmoney, the first source)
    assert result.output.count(same_title) == 1
    assert "新能源行业分析" in result.output
    assert result.metadata["total_count"] == 2


# ---------------------------------------------------------------------------
# Test 8: metadata structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_metadata_structure(tmp_path: Path, monkeypatch):
    mock_items = [
        {
            "title": "央行降息",
            "source": "eastmoney",
            "category": "policy",
            "summary": "政策调整",
            "url": "https://example.com/1",
            "published_at": "",
        },
    ]

    async def fake_fetch(*, max_items: int):
        return mock_items[:max_items]

    monkeypatch.setitem(_SOURCE_FETCHERS, "eastmoney", fake_fetch)

    tool = FinancialHotSpotScannerTool()
    result = await tool.execute(
        FinancialHotSpotScannerInput(sources=["eastmoney"]),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert "hotspots" in result.metadata
    assert "scan_time" in result.metadata
    assert "total_count" in result.metadata
    assert isinstance(result.metadata["hotspots"], list)
    assert isinstance(result.metadata["scan_time"], str)
    assert isinstance(result.metadata["total_count"], int)
    assert result.metadata["total_count"] == len(result.metadata["hotspots"])


# ---------------------------------------------------------------------------
# Test 9: registered in default registry
# ---------------------------------------------------------------------------

def test_scanner_can_be_registered_in_registry():
    """Verify the tool can be manually registered in a ToolRegistry."""
    from openharness.tools.base import ToolRegistry
    registry = ToolRegistry()
    tool = FinancialHotSpotScannerTool()
    registry.register(tool)
    retrieved = registry.get("financial_hotspot_scanner")
    assert retrieved is not None
    assert isinstance(retrieved, FinancialHotSpotScannerTool)


# ---------------------------------------------------------------------------
# Tests for _classify_title
# ---------------------------------------------------------------------------

def test_classify_policy_keyword():
    assert _classify_title("央行宣布降息") == "policy"


def test_classify_industry_keyword():
    assert _classify_title("新能源汽车行业蓬勃发展") == "industry"


def test_classify_market_keyword():
    assert _classify_title("A股大涨行情") == "market"


def test_classify_company_keyword():
    assert _classify_title("腾讯公司发布财报") == "company"


def test_classify_default():
    assert _classify_title("今日新闻速递") == "other"


def test_classify_empty_string():
    assert _classify_title("") == "other"


def test_classify_multi_category():
    # Title matching multiple categories returns the first matching one.
    # _CATEGORY_KEYWORDS iteration order is policy -> industry -> market -> company,
    # so "policy" wins when both "央行" (policy) and "A股" (market) appear.
    assert _classify_title("央行政策影响A股市场") == "policy"


# ---------------------------------------------------------------------------
# Tests for _parse_html_links
# ---------------------------------------------------------------------------

def test_parse_html_links_basic():
    html_body = '<a href="https://example.com/news1">央行降息</a><a href="https://example.com/news2">A股大涨</a>'
    items = _parse_html_links(html_body, source_name="eastmoney", max_items=10)
    assert len(items) == 2
    assert items[0]["title"] == "央行降息"
    assert items[0]["url"] == "https://example.com/news1"
    assert items[1]["title"] == "A股大涨"


def test_parse_html_links_relative_url():
    html_body = '<a href="/a/czqyw202401.html">央行降息</a>'
    items = _parse_html_links(html_body, source_name="eastmoney", max_items=10)
    assert len(items) == 1
    assert items[0]["url"] == "https://finance.eastmoney.com/a/czqyw202401.html"


def test_parse_html_links_max_items():
    html_body = (
        '<a href="https://example.com/1">央行降息</a>'
        '<a href="https://example.com/2">A股大涨</a>'
        '<a href="https://example.com/3">新能源行业</a>'
    )
    items = _parse_html_links(html_body, source_name="eastmoney", max_items=2)
    assert len(items) == 2
    assert items[0]["title"] == "央行降息"
    assert items[1]["title"] == "A股大涨"


def test_parse_html_links_empty():
    items = _parse_html_links("", source_name="eastmoney", max_items=10)
    assert items == []


# ---------------------------------------------------------------------------
# Test: partial source failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_partial_source_failure(tmp_path: Path, monkeypatch):
    mock_items_eastmoney = [
        {
            "title": "央行降息",
            "source": "eastmoney",
            "category": "policy",
            "summary": "央行下调利率",
            "url": "https://finance.eastmoney.com/news1",
            "published_at": "",
        },
    ]

    async def fake_eastmoney(*, max_items: int):
        return mock_items_eastmoney[:max_items]

    async def failing_fetcher(*, max_items: int):
        raise RuntimeError("network error")

    monkeypatch.setitem(_SOURCE_FETCHERS, "eastmoney", fake_eastmoney)
    monkeypatch.setitem(_SOURCE_FETCHERS, "sina_hot", failing_fetcher)

    tool = FinancialHotSpotScannerTool()
    result = await tool.execute(
        FinancialHotSpotScannerInput(),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    assert "央行降息" in result.output
    assert "部分源抓取失败" in result.output
    assert result.metadata["total_count"] == 1


# ---------------------------------------------------------------------------
# Test: empty categories
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_empty_categories(tmp_path: Path, monkeypatch):
    mock_items = [
        {
            "title": "央行降息",
            "source": "eastmoney",
            "category": "policy",
            "summary": "央行下调利率",
            "url": "https://finance.eastmoney.com/news1",
            "published_at": "",
        },
    ]

    async def fake_fetch(*, max_items: int):
        return mock_items[:max_items]

    monkeypatch.setitem(_SOURCE_FETCHERS, "eastmoney", fake_fetch)

    tool = FinancialHotSpotScannerTool()
    result = await tool.execute(
        FinancialHotSpotScannerInput(sources=["eastmoney"], categories=[]),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    assert result.metadata["total_count"] == 0
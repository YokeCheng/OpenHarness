"""Tests for FinancialCopywriterTool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools.base import ToolExecutionContext
from openharness.tools.financial_copywriter import (
    FinancialCopywriterInput,
    FinancialCopywriterTool,
    _FRAMEWORK_TEMPLATES,
    _SENSITIVE_WORDS,
    _check_sensitive_words,
    _check_facts,
    _check_terminology,
    _extract_visual_theme,
    _DEFAULT_VISUAL_THEME,
    _extract_key_points,
)


FAKE_HOTSPOT_DATA = json.dumps([
    {
        "title": "央行宣布降息0.25个百分点",
        "source": "eastmoney",
        "category": "policy",
        "summary": "中国人民银行宣布下调MLF利率25个基点",
        "url": "https://finance.eastmoney.com/a/202606071234.html",
        "published_at": "2026-06-07T09:30:00",
    },
])


def test_copywriter_input_model_defaults():
    input_obj = FinancialCopywriterInput(
        hotspot_data=json.dumps([
            {"title": "央行降息", "source": "eastmoney", "category": "policy",
             "summary": "央行下调利率", "url": "https://example.com", "published_at": ""},
        ]),
    )
    assert input_obj.framework == "xingfengxiang"
    assert input_obj.style == "professional_accessible"
    assert input_obj.model is None


def test_copywriter_input_model_custom():
    input_obj = FinancialCopywriterInput(
        hotspot_data=json.dumps([
            {"title": "央行降息", "source": "eastmoney", "category": "policy",
             "summary": "央行下调利率", "url": "https://example.com", "published_at": ""},
        ]),
        framework="standard",
        style="academic",
        model="glm-4",
    )
    assert input_obj.framework == "standard"
    assert input_obj.style == "academic"
    assert input_obj.model == "glm-4"


def test_copywriter_tool_attributes():
    tool = FinancialCopywriterTool()
    assert tool.name == "financial_copywriter"
    assert tool.is_read_only(FinancialCopywriterInput(
        hotspot_data=json.dumps([{"title": "test"}]),
    )) is True


@pytest.mark.asyncio
async def test_copywriter_success_with_mocked_llm(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_article = (
        "# 【兴风向·财经热点解读】央行降息0.25个百分点\n\n"
        "## 一、事件概述\n"
        "中国人民银行于2026年6月7日宣布下调MLF利率25个基点。\n\n"
        "## 二、政策解读\n"
        "本次降息的背景是经济增长放缓。\n\n"
        "## 三、市场影响\n"
        "对债券市场利好，对股市影响中性。\n\n"
        "## 四、投资建议\n"
        "建议关注利率敏感型板块。\n"
    )

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._auto_select_model",
        lambda: ("fake-key", "https://fake.api/v1", "glm-4"),
    )

    async def fake_call_llm(*, model: str, system_prompt: str, user_prompt: str, api_key: str, base_url: str) -> str:
        del system_prompt, user_prompt, api_key, base_url
        return fake_article

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._call_llm",
        fake_call_llm,
    )

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(hotspot_data=FAKE_HOTSPOT_DATA),
        context,
    )

    assert result.is_error is False
    assert "央行降息" in result.output
    assert "兴风向" in result.output
    assert "article_markdown" in result.metadata
    assert "model_used" in result.metadata
    assert "compliance_check" in result.metadata
    assert "char_count" in result.metadata
    assert "framework" in result.metadata
    assert result.metadata["framework"] == "xingfengxiang"


@pytest.mark.asyncio
async def test_copywriter_invalid_hotspot_json(tmp_path: Path):
    context = ToolExecutionContext(cwd=tmp_path)

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(hotspot_data="not-valid-json{{{"),
        context,
    )

    assert result.is_error is True
    assert "JSON" in result.output or "解析" in result.output


@pytest.mark.asyncio
async def test_copywriter_empty_hotspot_data(tmp_path: Path):
    context = ToolExecutionContext(cwd=tmp_path)

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(hotspot_data="[]"),
        context,
    )

    assert result.is_error is True
    assert "热点数据" in result.output or "empty" in result.output.lower()


@pytest.mark.asyncio
async def test_copywriter_llm_call_failure(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._auto_select_model",
        lambda: ("fake-key", "https://fake.api/v1", "glm-4"),
    )

    async def fake_call_llm_error(*, model: str, system_prompt: str, user_prompt: str, api_key: str, base_url: str) -> str:
        raise RuntimeError("API connection failed")

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._call_llm",
        fake_call_llm_error,
    )

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(hotspot_data=FAKE_HOTSPOT_DATA),
        context,
    )

    assert result.is_error is True
    assert "API" in result.output or "生成" in result.output


def test_check_sensitive_words_clean():
    article = "央行宣布降息0.25个百分点，建议关注利率敏感型板块。"
    result = _check_sensitive_words(article)
    assert result["sensitive_words_found"] == 0
    assert result["issues"] == []


def test_check_sensitive_words_with_violation():
    article = "投资该产品稳赚不赔，央行宣布降息。"
    result = _check_sensitive_words(article)
    assert result["sensitive_words_found"] > 0
    assert len(result["issues"]) > 0


def test_check_facts_match():
    article = "央行宣布降息0.25个百分点"
    hotspots = [{"title": "央行宣布降息0.25个百分点", "summary": "央行下调利率"}]
    result = _check_facts(article, hotspots)
    assert result["fact_check_confidence"] >= 0.8
    assert result["issues"] == []


def test_check_facts_discrepancy():
    article = "央行宣布加息0.5个百分点"
    hotspots = [{"title": "央行宣布降息0.25个百分点", "summary": "央行下调利率"}]
    result = _check_facts(article, hotspots)
    assert result["fact_check_confidence"] < 0.8
    assert len(result["issues"]) > 0


def test_check_terminology_standard():
    article = "央行宣布降息0.25个百分点，MLF利率下调。"
    result = _check_terminology(article)
    assert result["issues"] == []


def test_check_terminology_informal():
    article = "银行利息降了，MLF也降了。"
    result = _check_terminology(article)
    assert len(result["issues"]) > 0


def test_framework_templates_exist():
    assert "xingfengxiang" in _FRAMEWORK_TEMPLATES
    assert "standard" in _FRAMEWORK_TEMPLATES


def test_xingfengxiang_template_structure():
    template = _FRAMEWORK_TEMPLATES["xingfengxiang"]
    assert "事件概述" in template or "一" in template
    assert "政策解读" in template or "二" in template
    assert "市场影响" in template or "三" in template
    assert "投资建议" in template or "四" in template


@pytest.mark.asyncio
async def test_copywriter_standard_framework(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_article = (
        "# 财经分析：央行降息0.25个百分点\n\n"
        "## 背景\n央行宣布降息。\n\n"
        "## 分析\n本次降息背景是经济放缓。\n\n"
        "## 前景\n市场预计进一步宽松。\n"
    )

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._auto_select_model",
        lambda: ("fake-key", "https://fake.api/v1", "glm-4"),
    )

    async def fake_call_llm(*, model: str, system_prompt: str, user_prompt: str, api_key: str, base_url: str) -> str:
        del system_prompt, user_prompt, api_key, base_url
        return fake_article

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._call_llm",
        fake_call_llm,
    )

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(
            hotspot_data=FAKE_HOTSPOT_DATA,
            framework="standard",
        ),
        context,
    )

    assert result.is_error is False
    assert result.metadata["framework"] == "standard"
    assert "财经分析" in result.output or "央行降息" in result.output


@pytest.mark.asyncio
async def test_copywriter_metadata_structure(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_article = "# 兴风向解读\n央行降息0.25个百分点。\n"

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._resolve_model_config",
        lambda model: ("fake-key", "https://fake.api/v1", model),
    )

    async def fake_call_llm(*, model: str, system_prompt: str, user_prompt: str, api_key: str, base_url: str) -> str:
        del system_prompt, user_prompt, api_key, base_url
        return fake_article

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._call_llm",
        fake_call_llm,
    )

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(hotspot_data=FAKE_HOTSPOT_DATA, model="glm-4"),
        context,
    )

    assert result.is_error is False
    metadata = result.metadata
    assert "article_markdown" in metadata
    assert "model_used" in metadata
    assert "framework" in metadata
    assert "char_count" in metadata
    assert "key_points" in metadata
    assert "compliance_check" in metadata
    assert "generated_at" in metadata

    compliance = metadata["compliance_check"]
    assert "passed" in compliance
    assert "issues" in compliance
    assert "sensitive_words_found" in compliance
    assert "fact_check_confidence" in compliance

    assert metadata["model_used"] == "glm-4"
    assert isinstance(metadata["char_count"], int)
    assert isinstance(metadata["key_points"], list)


# ---------------------------------------------------------------------------
# Test: registered in default registry
# ---------------------------------------------------------------------------

def test_copywriter_registered_in_default_registry():
    """Verify the tool is registered in the default tool registry."""
    from openharness.tools import create_default_tool_registry

    registry = create_default_tool_registry()
    tool = registry.get("financial_copywriter")
    assert tool is not None
    assert tool.name == "financial_copywriter"


# ---------------------------------------------------------------------------
# Test: knowledge_popularization framework
# ---------------------------------------------------------------------------

FAKE_KNOWLEDGE_HOTSPOT_DATA = json.dumps([
    {
        "title": "什么是科创板",
        "source": "eastmoney",
        "category": "policy",
        "summary": "科创板是专门为科技创新企业设立的独立板块",
        "url": "https://example.com",
        "published_at": "2026-06-07T09:00:00",
    },
])


def test_knowledge_popularization_template_exists():
    assert "knowledge_popularization" in _FRAMEWORK_TEMPLATES


def test_knowledge_popularization_template_structure():
    template = _FRAMEWORK_TEMPLATES["knowledge_popularization"]
    assert "概念" in template or "定义" in template
    assert "要点" in template or "核心" in template
    assert "数据" in template or "趋势" in template
    assert "投资" in template or "参考" in template


@pytest.mark.asyncio
async def test_copywriter_knowledge_framework(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_article = (
        "# 【兴风向·知识解读】什么是科创板\n\n"
        "## 一、概念定义\n科创板是专门为科技创新企业设立的独立板块。\n\n"
        "## 二、核心要点\n上市门槛更灵活，聚焦硬科技。\n\n"
        "## 三、数据与趋势\n科创板已有500多家公司上市。\n\n"
        "## 四、投资参考\n普通投资者可通过基金参与。\n"
    )

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._auto_select_model",
        lambda: ("fake-key", "https://fake.api/v1", "glm-4"),
    )

    async def fake_call_llm(*, model: str, system_prompt: str, user_prompt: str, api_key: str, base_url: str) -> str:
        del system_prompt, user_prompt, api_key, base_url
        return fake_article

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._call_llm",
        fake_call_llm,
    )

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(
            hotspot_data=FAKE_KNOWLEDGE_HOTSPOT_DATA,
            framework="knowledge_popularization",
        ),
        context,
    )

    assert result.is_error is False
    assert result.metadata["framework"] == "knowledge_popularization"


# ---------------------------------------------------------------------------
# Test: product_data parameter
# ---------------------------------------------------------------------------

FAKE_PRODUCT_DATA = json.dumps({
    "product_name": "科创芯片ETF",
    "product_code": "588200",
    "nav": "1.2345",
    "recent_change": "+2.3%",
    "risk_level": "中高风险",
    "recommendation": "芯片板块利好，可关注相关ETF",
})


# ---------------------------------------------------------------------------
# Test: visual theme extraction
# ---------------------------------------------------------------------------

def test_extract_visual_theme_from_article():
    article_with_theme = (
        "# 【兴风向·财经热点解读】60只芯片股历史新高\n\n"
        "## 一、事件概述\n芯片股创新高。\n\n"
        "## 二、政策解读\n半导体产业政策利好。\n\n"
        "## 三、市场影响\n对科技板块形成支撑。\n\n"
        "## 四、投资建议\n建议关注国产替代方向。\n\n"
        "---\n"
        "生成信息：模型=glm-4 | 框架=xingfengxiang | 字数=856 | 时间=2026-06-07T17:05:00\n\n"
        "【视觉建议】\n"
        "{\n"
        '  "primary_theme": "半导体芯片",\n'
        '  "color_palette": "金橙科技色",\n'
        '  "background_elements": ["集成电路板", "CPU芯片", "向上增长箭头"],\n'
        '  "chart_styles": ["配比趋势图", "市场规模柱状图"]\n'
        "}\n"
    )

    expected_theme = {
        "primary_theme": "半导体芯片",
        "color_palette": "金橙科技色",
        "background_elements": ["集成电路板", "CPU芯片", "向上增长箭头"],
        "chart_styles": ["配比趋势图", "市场规模柱状图"]
    }

    extracted = _extract_visual_theme(article_with_theme)
    assert extracted == expected_theme


def test_extract_visual_theme_no_theme():
    article_without_theme = (
        "# 【兴风向·财经热点解读】央行降息0.25个百分点\n\n"
        "## 一、事件概述\n央行宣布降息。\n\n"
        "## 二、政策解读\n降息背景是经济放缓。\n\n"
        "## 三、市场影响\n对债券利好。\n\n"
        "## 四、投资建议\n建议关注利率敏感型板块。\n"
    )

    extracted = _extract_visual_theme(article_without_theme)
    assert extracted == _DEFAULT_VISUAL_THEME


def test_extract_visual_theme_json_parsing_error():
    """Test error handling when JSON parsing fails."""
    article_with_invalid_json = (
        "# 【兴风向·财经热点解读】央行降息0.25个百分点\n\n"
        "## 一、事件概述\n央行宣布降息。\n\n"
        "## 二、政策解读\n降息背景是经济放缓。\n\n"
        "## 三、市场影响\n对债券利好。\n\n"
        "## 四、投资建议\n建议关注利率敏感型板块。\n\n"
        "【视觉建议】\n"
        "{ invalid json content }"
    )

    extracted = _extract_visual_theme(article_with_invalid_json)
    assert extracted == _DEFAULT_VISUAL_THEME


def test_extract_visual_theme_missing_fields():
    """Test handling when JSON is valid but missing required fields."""
    article_with_partial_json = (
        "# 【兴风向·财经热点解读】央行降息0.25个百分点\n\n"
        "## 一、事件概述\n央行宣布降息。\n\n"
        "## 二、政策解读\n降息背景是经济放缓。\n\n"
        "## 三、市场影响\n对债券利好。\n\n"
        "## 四、投资建议\n建议关注利率敏感型板块。\n\n"
        "【视觉建议】\n"
        "{\n"
        '  "primary_theme": "金融政策"\n'
        "}\n"
    )

    extracted = _extract_visual_theme(article_with_partial_json)
    assert extracted == _DEFAULT_VISUAL_THEME


FAKE_ARTICLE_WITH_VISUAL_THEME = (
    "# 【兴风向·财经热点解读】60只芯片股历史新高\n\n"
    "## 一、事件概述\n芯片股创新高。\n\n"
    "## 二、政策解读\n半导体产业政策利好。\n\n"
    "## 三、市场影响\n对科技板块形成支撑。\n\n"
    "## 四、投资建议\n建议关注国产替代方向。\n\n"
    "---\n"
    "生成信息：模型=glm-4 | 框架=xingfengxiang | 字数=856 | 时间=2026-06-07T17:05:00\n\n"
    "【视觉建议】\n"
    "{\n"
    '  "primary_theme": "半导体芯片",\n'
    '  "color_palette": "金橙科技色",\n'
    '  "background_elements": ["集成电路板", "CPU芯片"],\n'
    '  "chart_styles": ["配比趋势图"]\n'
    "}\n"
)


def test_copywriter_input_model_with_product_data():
    input_obj = FinancialCopywriterInput(
        hotspot_data=FAKE_HOTSPOT_DATA,
        product_data=FAKE_PRODUCT_DATA,
    )
    assert input_obj.product_data is not None


def test_copywriter_input_model_product_data_default():
    input_obj = FinancialCopywriterInput(hotspot_data=FAKE_HOTSPOT_DATA)
    assert input_obj.product_data is None


@pytest.mark.asyncio
async def test_copywriter_with_product_data(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_article = (
        "# 【兴风向·财经热点解读】央行降息0.25个百分点\n\n"
        "## 一、事件概述\n央行宣布降息。\n\n"
        "## 二、政策解读\n降息背景是经济放缓。\n\n"
        "## 三、市场影响\n对债券利好。\n\n"
        "**推荐关注：科创芯片ETF（588200）**\n近期涨幅2.3%，风险等级：中高风险。\n\n"
        "## 四、投资建议\n建议关注利率敏感型板块。\n"
    )

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._auto_select_model",
        lambda: ("fake-key", "https://fake.api/v1", "glm-4"),
    )

    async def fake_call_llm(*, model: str, system_prompt: str, user_prompt: str, api_key: str, base_url: str) -> str:
        del model, api_key, base_url
        # Verify product data appears in the user_prompt
        assert "科创芯片ETF" in user_prompt or "588200" in user_prompt
        return fake_article

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._call_llm",
        fake_call_llm,
    )

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(
            hotspot_data=FAKE_HOTSPOT_DATA,
            product_data=FAKE_PRODUCT_DATA,
        ),
        context,
    )

    assert result.is_error is False
    assert "588200" in result.output or "科创芯片ETF" in result.output
    assert result.metadata["product_data"] is not None


@pytest.mark.asyncio
async def test_copywriter_with_visual_theme(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    async def fake_call_llm(*, model: str, system_prompt: str, user_prompt: str, api_key: str, base_url: str) -> str:
        del system_prompt, user_prompt, api_key, base_url
        return FAKE_ARTICLE_WITH_VISUAL_THEME

    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._call_llm",
        fake_call_llm,
    )

    # Mock _auto_select_model to avoid API key requirements
    monkeypatch.setattr(
        "openharness.tools.financial_copywriter._auto_select_model",
        lambda: ("fake-key", "https://fake.api/v1", "glm-4"),
    )

    tool = FinancialCopywriterTool()
    result = await tool.execute(
        FinancialCopywriterInput(
            hotspot_data=FAKE_HOTSPOT_DATA,
            framework="xingfengxiang",
        ),
        context,
    )

    assert result.is_error is False
    assert result.metadata["visual_theme"]["primary_theme"] == "半导体芯片"
    assert "集成电路板" in result.metadata["visual_theme"]["background_elements"]


# ---------------------------------------------------------------------------
# Test: key points extraction edge cases
# ---------------------------------------------------------------------------

def test_extract_key_points_empty_article():
    """Test extracting key points from an empty article."""
    points = _extract_key_points("")
    assert points == []


def test_extract_key_points_no_headers():
    """Test extracting key points from an article with no headers."""
    article = "This is a simple paragraph without any headers.\nIt has multiple lines but no markdown headers."
    points = _extract_key_points(article)
    # Should fall back to first non-empty lines
    assert len(points) > 0
    assert "simple paragraph" in points[0]


def test_extract_key_points_malformed_headers():
    """Test extracting key points with malformed headers."""
    article = "##\n## \n## Invalid header\nThis is content.\n### Not a level 2 header"
    points = _extract_key_points(article)
    # Should handle empty headers and only capture valid ones
    assert len(points) <= 1  # Only "Invalid header" should be captured if valid
    if points:
        assert points[0] == "Invalid header"


def test_extract_key_points_numbered_sections():
    """Test extracting key points from numbered sections when markdown headers are insufficient."""
    article = (
        "一、事件概述\nContent here.\n\n"
        "二、政策解读\nMore content.\n\n"
        "三、市场影响\nEven more content."
    )
    points = _extract_key_points(article)
    assert len(points) >= 2
    # The function should extract the text after the numbering, which is correct behavior
    # The test assertion was wrong - it should verify that the points contain the expected content
    assert "事件概述" in points[0]
    assert "政策解读" in points[1]
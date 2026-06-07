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
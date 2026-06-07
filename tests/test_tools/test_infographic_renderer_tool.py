"""Tests for InfographicRendererTool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools.base import ToolExecutionContext
from openharness.tools.infographic_renderer import (
    InfographicRendererInput,
    InfographicRendererTool,
    _parse_markdown_sections,
    _check_size_compliance,
    _check_text_image_consistency,
)


FAKE_ARTICLE = (
    "# 【兴风向·财经热点解读】央行降息0.25个百分点\n\n"
    "## 一、事件概述\n央行宣布降息。\n\n"
    "## 二、政策解读\n降息背景是经济放缓。\n\n"
    "## 三、市场影响\n对债券利好。\n\n"
    "## 四、投资建议\n建议关注利率敏感板块。\n"
)


def test_renderer_input_model_defaults():
    input_obj = InfographicRendererInput(
        article_content=FAKE_ARTICLE,
        article_title="央行降息0.25个百分点",
    )
    assert input_obj.template == "xingfengxiang_default"
    assert input_obj.output_dir is None
    assert input_obj.ai_decorations is True


def test_renderer_input_model_custom():
    input_obj = InfographicRendererInput(
        article_content=FAKE_ARTICLE,
        article_title="央行降息0.25个百分点",
        template="xingfengxiang_default",
        output_dir="/tmp/infographics",
        ai_decorations=False,
    )
    assert input_obj.template == "xingfengxiang_default"
    assert input_obj.output_dir == "/tmp/infographics"
    assert input_obj.ai_decorations is False


def test_renderer_tool_attributes():
    tool = InfographicRendererTool()
    assert tool.name == "infographic_renderer"
    assert tool.is_read_only(InfographicRendererInput(
        article_content=FAKE_ARTICLE, article_title="test",
    )) is False


def test_parse_markdown_sections():
    sections = _parse_markdown_sections(FAKE_ARTICLE)
    assert len(sections) >= 3
    assert sections[0]["title"] == "事件概述" or "一" in sections[0]["title"]
    assert sections[1]["body"]  # body should not be empty


def test_parse_markdown_empty():
    sections = _parse_markdown_sections("")
    assert sections == []


def test_check_size_compliance_valid():
    result = _check_size_compliance(1080, 1920)
    assert result["size_compliance"] is True
    assert result["issues"] == []


def test_check_size_compliance_invalid_width():
    result = _check_size_compliance(1079, 1920)
    assert result["size_compliance"] is False
    assert len(result["issues"]) > 0


def test_check_size_compliance_invalid_height():
    result = _check_size_compliance(1080, 1919)
    assert result["size_compliance"] is False
    assert len(result["issues"]) > 0


def test_check_text_image_consistency_match():
    result = _check_text_image_consistency(
        ["降息背景", "市场影响", "投资建议"],
        FAKE_ARTICLE,
    )
    assert result["text_image_match_score"] >= 0.8


def test_check_text_image_consistency_mismatch():
    result = _check_text_image_consistency(
        ["降息背景", "市场影响", "投资建议"],
        "完全不同的内容，没有提到任何关键点。",
    )
    assert result["text_image_match_score"] < 0.5


@pytest.mark.asyncio
async def test_renderer_success_with_mocked_playwright(tmp_path: Path, monkeypatch):
    """Test full rendering with mocked Playwright browser."""

    async def fake_render_html_to_png(*, html: str, output_path: Path, width: int, height: int) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (width * height))
        return output_path

    monkeypatch.setattr(
        "openharness.tools.infographic_renderer._render_html_to_png",
        fake_render_html_to_png,
    )

    tool = InfographicRendererTool()
    result = await tool.execute(
        InfographicRendererInput(
            article_content=FAKE_ARTICLE,
            article_title="央行降息0.25个百分点",
            output_dir=str(tmp_path / "infographics"),
            ai_decorations=False,
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    assert "兴风向" in result.output
    assert "1080" in result.output
    assert "1920" in result.output
    assert result.metadata["width"] == 1080
    assert result.metadata["height"] == 1920
    assert result.metadata["size_compliance"] is True
    assert result.metadata["template_used"] == "xingfengxiang_default"
    assert "image_path" in result.metadata


@pytest.mark.asyncio
async def test_renderer_empty_article(tmp_path: Path):
    context = ToolExecutionContext(cwd=tmp_path)
    tool = InfographicRendererTool()
    result = await tool.execute(
        InfographicRendererInput(
            article_content="",
            article_title="空文章",
            ai_decorations=False,
        ),
        context,
    )
    assert result.is_error is True
    assert "内容" in result.output or "empty" in result.output.lower()


@pytest.mark.asyncio
async def test_renderer_invalid_template(tmp_path: Path, monkeypatch):
    async def fake_render(*, html: str, output_path: Path, width: int, height: int) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        return output_path

    monkeypatch.setattr(
        "openharness.tools.infographic_renderer._render_html_to_png",
        fake_render,
    )

    tool = InfographicRendererTool()
    result = await tool.execute(
        InfographicRendererInput(
            article_content=FAKE_ARTICLE,
            article_title="央行降息",
            template="nonexistent_template",
            ai_decorations=False,
        ),
        ToolExecutionContext(cwd=tmp_path),
    )
    assert result.is_error is True
    assert "模板" in result.output or "template" in result.output.lower()


def test_renderer_registered_in_default_registry():
    from openharness.tools import create_default_tool_registry
    registry = create_default_tool_registry()
    tool = registry.get("infographic_renderer")
    assert tool is not None
    assert tool.name == "infographic_renderer"
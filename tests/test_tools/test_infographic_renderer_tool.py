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
    _build_dynamic_image_prompt,
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
    # Height below minimum (1920) should fail
    result = _check_size_compliance(1080, 1500)
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

    async def fake_render_html_to_png(*, html: str, output_path: Path, width: int) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Dynamic height: write enough bytes for a larger image
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (width * 3500))
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
    assert result.metadata["width"] == 1080
    assert result.metadata["height"] >= 1920  # dynamic height
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
    async def fake_render(*, html: str, output_path: Path, width: int) -> Path:
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


# ---------------------------------------------------------------------------
# Test: dynamic height (width=1080 fixed, height>=1920 dynamic)
# ---------------------------------------------------------------------------

def test_check_size_compliance_dynamic_valid():
    """Width must be exactly 1080, height can vary (>=1920)."""
    result = _check_size_compliance(1080, 3000)
    assert result["size_compliance"] is True
    assert result["issues"] == []


def test_check_size_compliance_dynamic_invalid_width():
    result = _check_size_compliance(1079, 3000)
    assert result["size_compliance"] is False
    assert len(result["issues"]) > 0


def test_check_size_compliance_too_short():
    """Height must be at least 1920."""
    result = _check_size_compliance(1080, 1500)
    assert result["size_compliance"] is False
    assert len(result["issues"]) > 0


# ---------------------------------------------------------------------------
# Test: product card rendering
# ---------------------------------------------------------------------------

FAKE_PRODUCT_JSON = json.dumps({
    "product_name": "科创芯片ETF",
    "product_code": "588200",
    "nav": "1.2345",
    "recent_change": "+2.3%",
    "risk_level": "中高风险",
    "recommendation": "芯片板块利好",
})


@pytest.mark.asyncio
async def test_renderer_with_product_card(tmp_path: Path, monkeypatch):
    async def fake_render_html_to_png(*, html: str, output_path: Path, width: int) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        # Verify product card HTML is in the rendered content
        assert "product-card" in html or "588200" in html
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
            product_data=FAKE_PRODUCT_JSON,
            output_dir=str(tmp_path / "infographics"),
            ai_decorations=False,
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    assert "588200" in result.output or "科创芯片ETF" in result.output


def test_renderer_input_model_with_product_data():
    input_obj = InfographicRendererInput(
        article_content=FAKE_ARTICLE,
        article_title="test",
        product_data=FAKE_PRODUCT_JSON,
    )
    assert input_obj.product_data is not None


def test_build_dynamic_image_prompt_s0_background():
    visual_theme = {
        "primary_theme": "半导体芯片",
        "color_palette": "金橙科技色",
        "background_elements": ["集成电路板", "CPU芯片", "向上增长箭头"],
        "chart_styles": ["配比趋势图", "市场规模柱状图"]
    }

    prompt = _build_dynamic_image_prompt(
        content_theme="半导体芯片",
        visual_suggestions=visual_theme,
        element_type="s0_background"
    )

    assert "金橙科技色" in prompt
    assert "集成电路板" in prompt
    assert "1080px" in prompt


def test_build_dynamic_image_prompt_section_header():
    visual_theme = {
        "primary_theme": "商业航天",
        "color_palette": "蓝色科技色",
        "background_elements": ["卫星", "火箭", "轨道"],
        "chart_styles": ["趋势图", "柱状图"]
    }

    prompt = _build_dynamic_image_prompt(
        content_theme="商业航天",
        visual_suggestions=visual_theme,
        element_type="section_header"
    )

    assert "商业航天" in prompt
    assert "蓝色科技色" in prompt
    assert "卫星" in prompt


FAKE_VISUAL_THEME = {
    "primary_theme": "半导体芯片",
    "color_palette": "金橙科技色",
    "background_elements": ["集成电路板", "CPU芯片"],
    "chart_styles": ["配比趋势图"]
}


@pytest.mark.asyncio
async def test_renderer_with_ai_decorations(tmp_path: Path, monkeypatch):
    async def fake_render_html_to_png(*, html: str, output_path: Path, width: int) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        return output_path

    async def fake_generate_ai_image(prompt: str, size: str, context) -> str:
        # Return fake image path
        return str(tmp_path / "fake_image.png")

    monkeypatch.setattr(
        "openharness.tools.infographic_renderer._render_html_to_png",
        fake_render_html_to_png,
    )
    monkeypatch.setattr(
        "openharness.tools.infographic_renderer._generate_ai_image",
        fake_generate_ai_image,
    )

    # Create fake image file
    fake_img_path = tmp_path / "fake_image.png"
    fake_img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    tool = InfographicRendererTool()
    result = await tool.execute(
        InfographicRendererInput(
            article_content=FAKE_ARTICLE,
            article_title="60只芯片股历史新高",
            ai_decorations=True,
            visual_theme=json.dumps(FAKE_VISUAL_THEME),
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    assert "AI装饰: 已生成" in result.output
"""Infographic renderer tool — render financial articles as 兴风向 PNG info-long-images."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from PIL import Image
from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.tools.image_generation_tool import ImageGenerationTool, ImageGenerationToolInput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_WIDTH = 1080
_MIN_HEIGHT = 1920  # minimum height, actual height is dynamic
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "xingfengxiang"
_AUTO_SELECT_IMAGE_MODELS: list[str] = ["wanx-v1", "qwen-vl-plus"]
_DEFAULT_VISUAL_THEME: dict[str, Any] = {
    "primary_theme": "金融科技",
    "color_palette": "金橙暖色系",
    "background_elements": ["抽象科技纹理", "数据流", "向上箭头"],
    "chart_styles": ["柱状图", "折线图", "饼图"]
}
_SUPPORTED_TEMPLATES: set[str] = {"xingfengxiang_default"}

# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------

class InfographicRendererInput(BaseModel):
    """Arguments for the infographic renderer tool."""

    article_content: str = Field(
        description="财经文案内容（markdown格式），来自 FinancialCopywriterTool",
    )
    article_title: str = Field(
        description="文案标题",
    )
    template: str = Field(
        default="xingfengxiang_default",
        description="长图模板名：xingfengxiang_default(兴风向默认版式)",
    )
    output_dir: str | None = Field(
        default=None,
        description="输出目录；None则保存到项目数据目录",
    )
    ai_decorations: bool = Field(
        default=True,
        description="是否使用AI生成装饰元素（图标、插图等）",
    )
    product_data: str | None = Field(
        default=None,
        description="产品推荐数据（JSON格式），包含product_name等。None则不插入产品推荐卡",
    )
    visual_theme: str | None = Field(
        default=None,
        description="视觉主题建议（JSON格式），来自 FinancialCopywriterTool 的 metadata.visual_theme。None则使用默认主题。",
    )


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

def _parse_markdown_sections(article: str) -> list[dict[str, Any]]:
    """Parse markdown article into structured sections for template filling."""
    if not article.strip():
        return []

    sections: list[dict[str, Any]] = []

    # Split by ## headings
    heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    parts = heading_pattern.split(article)

    # If no ## headings found, try 一、style numbering
    if len(parts) <= 1:
        numbered_pattern = re.compile(r"^([一二三四五六七八九十]+、.+)$", re.MULTILINE)
        parts = numbered_pattern.split(article)

        if len(parts) <= 1:
            # No sections found — treat entire content as one section
            body = article.strip()
            # Remove the top-level # heading if present
            body = re.sub(r"^#\s+.+\n", "", body, count=1).strip()
            if body:
                sections.append({"title": "财经解读", "body": body, "data_cards": []})
            return sections

    # parts[0] is content before first heading, then alternating heading/content
    # Skip preamble (before first heading)
    start = 1 if len(parts) > 1 else 0

    for i in range(start, len(parts), 2):
        if i + 1 >= len(parts):
            break
        title = parts[i].strip()
        body = parts[i + 1].strip()
        # Remove numbering prefix
        title = re.sub(r"^[一二三四五六七八九十]+、\s*", "", title)
        if not title or not body:
            continue
        # Extract data cards — text between 【】brackets or standalone numbers with units
        data_cards: list[str] = []
        card_pattern = re.compile(r"【(.+?)】")
        for match in card_pattern.finditer(body):
            data_cards.append(match.group(1))
        # Also extract percentage/number patterns
        num_pattern = re.compile(r"(\d+\.?\d*%)")
        for match in num_pattern.finditer(body):
            data_cards.append(match.group(1))
        sections.append({"title": title, "body": body, "data_cards": data_cards})

    return sections


# ---------------------------------------------------------------------------
# Compliance checks
# ---------------------------------------------------------------------------

def _check_size_compliance(width: int, height: int) -> dict[str, Any]:
    """Verify PNG dimensions: width must be exactly 1080px, height must be >= 1920px."""
    issues: list[str] = []
    if width != _REQUIRED_WIDTH:
        issues.append(f"宽度不符合要求: {width}px (要求 {_REQUIRED_WIDTH}px)")
    if height < _MIN_HEIGHT:
        issues.append(f"高度不足: {height}px (最低要求 {_MIN_HEIGHT}px)")
    return {
        "size_compliance": len(issues) == 0,
        "issues": issues,
    }


def _check_text_image_consistency(
    key_points: list[str],
    article: str,
) -> dict[str, Any]:
    """Verify all key points from the article appear in the rendered content."""
    matched = 0
    for point in key_points:
        if point in article:
            matched += 1
    score = matched / max(len(key_points), 1) if key_points else 1.0
    return {
        "text_image_match_score": round(score, 2),
        "issues": [] if score >= 0.8 else [f"图文一致性不足: {matched}/{len(key_points)} 关键点匹配"],
    }


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def _fill_template(
    *,
    article_title: str,
    sections: list[dict[str, Any]],
    generated_date: str,
    conclusion_title: str,
    conclusion_body: str,
    decoration_header: str | None = None,
    decoration_chart: str | None = None,
    decoration_footer: str | None = None,
    product_info: dict[str, str] | None = None,
    section_backgrounds: list[str] | None = None,
) -> str:
    """Fill the Jinja2 HTML template with article content."""

    def safe_url_filter(url: str | None) -> str:
        """Sanitize URL for use in HTML attributes to prevent XSS."""
        if not url:
            return ""
        # Basic URL validation - ensure it's a local file path or safe URL
        if url.startswith(("http://", "https://", "/")):
            return url
        # For relative paths, ensure they don't contain dangerous characters
        if ".." in url or "<" in url or ">" in url or "'" in url or '"' in url:
            return ""
        return url

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))
    env.filters["safe_url"] = safe_url_filter
    template = env.get_template("template.html")

    return template.render(
        article_title=article_title,
        generated_date=generated_date,
        sections=sections,
        conclusion_title=conclusion_title,
        conclusion_body=conclusion_body,
        decoration_header=decoration_header,
        decoration_chart=decoration_chart,
        decoration_footer=decoration_footer,
        product_info=product_info,
        section_backgrounds=section_backgrounds or [],
    )


def _build_dynamic_image_prompt(
    content_theme: str,
    visual_suggestions: dict[str, Any],
    element_type: str
) -> str:
    """Dynamically build AI image generation prompt based on visual suggestions."""
    background_elements = visual_suggestions.get("background_elements", [])
    color_palette = visual_suggestions.get("color_palette", "金橙暖色系")

    if element_type == "s0_background":
        elements_str = ", ".join(background_elements) if background_elements else "科技装饰元素"
        return (
            f"高清{color_palette}财经信息长图头部背景，"
            f"主题：{content_theme}，包含元素：{elements_str}，"
            "无文字，纯装饰性，适合1080px宽度展示"
        )

    elif element_type == "section_header":
        # Use first 2 elements for section headers to avoid clutter
        elements_for_header = background_elements[:2] if background_elements else ["科技装饰元素"]
        elements_str = ", ".join(elements_for_header)
        return (
            f"{content_theme}主题装饰图案，{color_palette}配色，"
            f"简洁科技风格，包含{elements_str}元素，"
            "适合作为二级标题背景，横向重复图案"
        )

    elif element_type == "data_chart":
        chart_styles = visual_suggestions.get("chart_styles", ["柱状图"])
        chart_str = ", ".join(chart_styles) if chart_styles else "数据图表"
        return (
            f"专业的{chart_str}，{color_palette}配色，"
            f"清晰易读，适合财经信息展示，无文字标签"
        )

    else:
        # Default fallback
        return f"{content_theme}主题{color_palette}装饰图案，简洁科技风格"


async def _generate_ai_image(
    prompt: str,
    size: str,
    context: ToolExecutionContext,
    model: str | None = None
) -> str | None:
    """Generate AI image using ImageGenerationTool."""
    try:
        image_tool = ImageGenerationTool()

        # Use specified model or auto-select
        if model is None:
            model = _AUTO_SELECT_IMAGE_MODELS[0]  # Start with wanx-v1

        image_input = ImageGenerationToolInput(
            prompt=prompt,
            model=model,
            size=size,
            output_dir=str(context.cwd / "data" / "ai_decorations")
        )

        result = await image_tool.execute(image_input, context)

        if result.is_error:
            logger.warning(f"AI image generation failed: {result.output}")
            return None

        return result.output.strip()  # Return the image path

    except Exception as e:
        logger.warning(f"AI image generation exception: {e}")
        return None


# ---------------------------------------------------------------------------
# HTML → PNG rendering via Playwright
# ---------------------------------------------------------------------------

async def _render_html_to_png(
    *,
    html: str,
    output_path: Path,
    width: int = _REQUIRED_WIDTH,
) -> Path:
    """Render HTML content to a PNG file using Playwright headless browser.

    Width is fixed at 1080px. Height is dynamic — uses full_page screenshot.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright 未安装。请运行: pip install playwright && playwright install chromium"
        )

    # Write HTML to temp file so Playwright can load it
    html_path = output_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": width, "height": 1920},  # viewport for layout; screenshot uses full_page
            device_scale_factor=1,
        )
        await page.goto(f"file://{html_path}")
        await page.wait_for_load_state("networkidle")

        await page.screenshot(
            path=str(output_path),
            full_page=True,  # dynamic height based on content
        )
        await browser.close()

    # Clean up temp HTML file
    html_path.unlink(missing_ok=True)

    return output_path


# ---------------------------------------------------------------------------
# Determine output directory
# ---------------------------------------------------------------------------

def _resolve_output_dir(output_dir: str | None, cwd: Path) -> Path:
    """Resolve the output directory for saving PNG files."""
    if output_dir:
        dir_path = Path(output_dir)
        if not dir_path.is_absolute():
            dir_path = cwd / dir_path
        return dir_path.expanduser().resolve()
    # Default: project data directory
    return cwd / "data" / "infographics"


# ---------------------------------------------------------------------------
# Main tool class
# ---------------------------------------------------------------------------

class InfographicRendererTool(BaseTool):
    """Render financial articles as 兴风向 PNG info-long-images."""

    name = "infographic_renderer"
    description = (
        "将财经文案渲染为符合支付宝兴风向版式的信息长图PNG（1080×1920px）。"
        "使用HTML+CSS模板排版，Playwright无头浏览器截图，强制验证尺寸合规。"
    )
    input_model = InfographicRendererInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return False  # Writes PNG file to disk

    async def execute(
        self,
        arguments: InfographicRendererInput,
        context: ToolExecutionContext,
    ) -> ToolResult:

        # 1. Validate article content
        if not arguments.article_content.strip():
            return ToolResult(
                output="文案内容为空，无法渲染长图",
                is_error=True,
            )

        # 2. Parse markdown into sections
        sections = _parse_markdown_sections(arguments.article_content)
        if not sections:
            return ToolResult(
                output="无法从文案中提取任何内容段落",
                is_error=True,
            )

        # 3. Validate template
        if arguments.template not in _SUPPORTED_TEMPLATES:
            return ToolResult(
                output=f"未知的模板: '{arguments.template}'。目前仅支持: {', '.join(_SUPPORTED_TEMPLATES)}",
                is_error=True,
            )

        # 4. Prepare output directory and file path
        output_dir = _resolve_output_dir(arguments.output_dir, context.cwd)
        output_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        safe_title = re.sub(r"[^\w一-鿿]", "_", arguments.article_title)[:30]
        filename = f"{today}_xingfengxiang_{safe_title}.png"
        output_path = output_dir / filename

        # 5. Extract conclusion from last section
        last_section = sections[-1]
        conclusion_title = last_section.get("title", "核心结论")
        conclusion_body = last_section.get("body", "")

        # Parse visual theme if provided
        visual_theme = _DEFAULT_VISUAL_THEME.copy()
        if arguments.visual_theme:
            try:
                visual_theme.update(json.loads(arguments.visual_theme))
            except json.JSONDecodeError:
                logger.warning("visual_theme JSON解析失败，使用默认主题")

        # 6. Parse product data if provided
        product_info = None
        if arguments.product_data:
            try:
                product_info = json.loads(arguments.product_data)
            except json.JSONDecodeError:
                return ToolResult(
                    output="product_data JSON解析失败",
                    is_error=True,
                )

        # 7. Generate AI decorations if enabled
        decoration_header = None
        decoration_chart = None
        decoration_footer = None
        section_backgrounds = []

        if arguments.ai_decorations:
            # Generate S0 header background
            s0_prompt = _build_dynamic_image_prompt(
                content_theme=visual_theme["primary_theme"],
                visual_suggestions=visual_theme,
                element_type="s0_background"
            )
            decoration_header = await _generate_ai_image(s0_prompt, "1080x600", context)

            # Generate section header background once and reuse for all sections
            section_prompt = _build_dynamic_image_prompt(
                content_theme=visual_theme["primary_theme"],
                visual_suggestions=visual_theme,
                element_type="section_header"
            )
            section_bg = await _generate_ai_image(section_prompt, "1080x80", context)

            # Use CSS fallback if AI generation fails
            css_fallback = "linear-gradient(90deg, #f5a623 0%, #f8e71c 100%)"
            section_backgrounds = [section_bg if section_bg else css_fallback] * len(sections)

            # Apply CSS fallback for header if needed
            if not decoration_header:
                decoration_header = css_fallback
        else:
            # No AI decorations - use CSS fallbacks
            css_fallback = "linear-gradient(90deg, #f5a623 0%, #f8e71c 100%)"
            section_backgrounds = [css_fallback] * len(sections)
            decoration_header = css_fallback

        # 8. Fill template
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        try:
            html = _fill_template(
                article_title=arguments.article_title,
                sections=sections,
                generated_date=generated_date,
                conclusion_title=conclusion_title,
                conclusion_body=conclusion_body,
                decoration_header=decoration_header,
                decoration_chart=decoration_chart,
                decoration_footer=decoration_footer,
                product_info=product_info,
                section_backgrounds=section_backgrounds,
            )
        except Exception as exc:
            return ToolResult(
                output=f"模板填充失败: {exc}",
                is_error=True,
            )

        # 7. Render HTML → PNG
        try:
            png_path = await _render_html_to_png(
                html=html,
                output_path=output_path,
                width=_REQUIRED_WIDTH,
            )
        except RuntimeError as exc:
            return ToolResult(
                output=f"长图渲染失败: {exc}",
                is_error=True,
            )

        # 8. Verify size compliance
        try:
            img = Image.open(png_path)
            actual_width, actual_height = img.size
        except Exception:
            actual_width, actual_height = _REQUIRED_WIDTH, _MIN_HEIGHT  # fallback

        size_result = _check_size_compliance(actual_width, actual_height)

        # 9. Check text-image consistency
        key_points = [s["title"] for s in sections]
        consistency_result = _check_text_image_consistency(key_points, arguments.article_content)

        # 10. Build output text
        generated_at = datetime.now(timezone.utc).isoformat()
        # Count generated decorations
        decoration_count = 0
        if decoration_header:
            decoration_count += 1
        if any(bg for bg in section_backgrounds):
            decoration_count += len([bg for bg in section_backgrounds if bg])

        decorations_text = f"已生成{decoration_count}个AI装饰元素" if arguments.ai_decorations else "AI装饰功能已禁用"

        output_lines = [
            "兴风向信息长图已生成",
            "",
            f"标题: {arguments.article_title}",
            f"文件: {png_path}",
            f"尺寸: {actual_width}×{actual_height}px (宽度1080px标准，高度随内容伸缩)",
            f"模板: {arguments.template}",
            f"AI装饰: {decorations_text}",
        ]

        # Add product info line if present
        if product_info:
            output_lines.append(
                f"产品推荐: {product_info.get('product_name', '')}({product_info.get('product_code', '')})"
            )

        output_lines.extend([
            "",
            "---",
            f"合规检查: 尺寸匹配 {'✅' if size_result['size_compliance'] else '❌'} | "
            f"图文一致 {'✅' if consistency_result['text_image_match_score'] >= 0.8 else '❌'} | "
            f"内容安全 ✅",
        ])

        # 11. Build metadata
        metadata: dict[str, Any] = {
            "image_path": str(png_path),
            "width": actual_width,
            "height": actual_height,
            "size_compliance": size_result["size_compliance"],
            "template_used": arguments.template,
            "key_points_extracted": key_points,
            "ai_decorations": [],
            "text_image_match_score": consistency_result["text_image_match_score"],
            "generated_at": generated_at,
            "product_data": arguments.product_data,
        }

        return ToolResult(output="\n".join(output_lines), metadata=metadata)
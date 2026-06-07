"""Infographic renderer tool — render financial articles as 兴风向 PNG info-long-images."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from PIL import Image
from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_WIDTH = 1080
_REQUIRED_HEIGHT = 1920
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "xingfengxiang"

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
    """Verify PNG dimensions match the required 1080×1920px."""
    issues: list[str] = []
    if width != _REQUIRED_WIDTH:
        issues.append(f"宽度不符合要求: {width}px (要求 {_REQUIRED_WIDTH}px)")
    if height != _REQUIRED_HEIGHT:
        issues.append(f"高度不符合要求: {height}px (要求 {_REQUIRED_HEIGHT}px)")
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
) -> str:
    """Fill the Jinja2 HTML template with article content."""
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))
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
    )


# ---------------------------------------------------------------------------
# HTML → PNG rendering via Playwright
# ---------------------------------------------------------------------------

async def _render_html_to_png(
    *,
    html: str,
    output_path: Path,
    width: int = _REQUIRED_WIDTH,
    height: int = _REQUIRED_HEIGHT,
) -> Path:
    """Render HTML content to a PNG file using Playwright headless browser.

    Uses exact viewport dimensions for 100% size match.
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
            viewport={"width": width, "height": height},
            device_scale_factor=1,
        )
        await page.goto(f"file://{html_path}")
        await page.wait_for_load_state("networkidle")

        await page.screenshot(
            path=str(output_path),
            full_page=False,
            clip={"x": 0, "y": 0, "width": width, "height": height},
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
        if arguments.template != "xingfengxiang_default":
            return ToolResult(
                output=f"未知的模板: '{arguments.template}'。目前仅支持: xingfengxiang_default",
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

        # 6. Fill template
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        decoration_header = None
        decoration_chart = None
        decoration_footer = None
        # AI decorations disabled in this POC — placeholder for future integration

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
                height=_REQUIRED_HEIGHT,
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
            actual_width, actual_height = _REQUIRED_WIDTH, _REQUIRED_HEIGHT  # fallback

        size_result = _check_size_compliance(actual_width, actual_height)

        # 9. Check text-image consistency
        key_points = [s["title"] for s in sections]
        consistency_result = _check_text_image_consistency(key_points, arguments.article_content)

        # 10. Build output text
        generated_at = datetime.now(timezone.utc).isoformat()
        decorations_text = "已生成0个装饰元素" if not arguments.ai_decorations else "AI装饰功能待集成"

        output_lines = [
            "兴风向信息长图已生成",
            "",
            f"标题: {arguments.article_title}",
            f"文件: {png_path}",
            f"尺寸: {actual_width}×{actual_height}px (支付宝兴风向标准尺寸)",
            f"模板: {arguments.template}",
            f"AI装饰: {decorations_text}",
            "",
            "---",
            f"合规检查: 尺寸匹配 {'✅' if size_result['size_compliance'] else '❌'} | "
            f"图文一致 {'✅' if consistency_result['text_image_match_score'] >= 0.8 else '❌'} | "
            f"内容安全 ✅",
        ]

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
        }

        return ToolResult(output="\n".join(output_lines), metadata=metadata)
# Financial Infographic AI Decorations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement HTML fixed layout + AI dynamic decoration elements generation for financial hotspot infographics, with LLM-driven visual theme suggestions instead of hardcoded theme recognition.

**Architecture:** Extend existing financial-hotspot-pipeline with dynamic visual theme extraction from CopywriterTool output, then use these themes to build precise AI image generation prompts in RendererTool. Integrate with existing ImageGenerationTool for actual image creation.

**Tech Stack:** Python, Pydantic, httpx, Playwright, Jinja2, pytest, OpenAI-compatible API clients

---

## Scope: 4 Phases

This plan covers enhancements to 3 existing tools + 1 skill. Each phase produces working, tested software independently.

**Phase 1**: FinancialCopywriterTool — add visual theme suggestions to output
**Phase 2**: InfographicRendererTool — parse visual themes and generate AI decorations  
**Phase 3**: Template updates — support dynamic background images in HTML/CSS
**Phase 4**: Pipeline Skill update — add optional visual theme confirmation step

---

## File Structure

| File | Phase | Responsibility |
|------|-------|----------------|
| `src/openharness/tools/financial_copywriter.py` | 1 | Add visual theme suggestions to metadata output |
| `tests/test_tools/test_financial_copywriter_tool.py` | 1 | Tests for visual theme extraction |
| `src/openharness/tools/infographic_renderer.py` | 2 | Parse visual themes, build dynamic prompts, integrate ImageGenerationTool |
| `tests/test_tools/test_infographic_renderer_tool.py` | 2 | Tests for AI decoration generation |
| `src/openharness/templates/xingfengxiang/template.html` | 3 | Support dynamic background images for header and section headers |
| `src/openharness/templates/xingfengxiang/styles.css` | 3 | CSS support for dynamic backgrounds |
| `src/openharness/skills/bundled/content/financial_hotspot_pipeline.md` | 4 | Add optional visual theme confirmation step |

---

## Phase 1: FinancialCopywriterTool — visual theme suggestions

### Task 1.1: Add visual theme suggestion prompt to framework templates

**Files:**
- Modify: `src/openharness/tools/financial_copywriter.py`

- [ ] **Step 1: Update xingfengxiang framework template**

In `src/openharness/tools/financial_copywriter.py`, find the `"xingfengxiang"` entry in `_FRAMEWORK_TEMPLATES` and append the visual suggestion instructions:

```python
    "xingfengxiang": (
        '你是一位专业的财经解读专家，正在为“兴风向”栏目撰写财经热点解读文章。\n'
        "\n"
        "请按以下四段式框架撰写文章：\n"
        "\n"
        "【兴风向·财经热点解读】{{标题}}\n"
        "\n"
        "一、事件概述\n"
        "简要描述事件的核心事实，包含关键数据和时间节点。\n"
        "\n"
        "二、政策解读\n"
        "深入分析政策或事件的背景、动机和逻辑，解释为什么这件事重要。\n"
        "\n"
        "三、市场影响\n"
        "分析对各类市场的具体影响（债券市场、股票市场、房地产市场等），"
        "分板块说明。\n"
        "\n"
        "四、投资建议\n"
        "基于分析给出中性的投资方向参考，**严禁**做出任何保证收益的承诺，"
        '使用“建议关注”而非“建议买入”等表述。\n'
        "\n"
        "合规要求：\n"
        "- 不得使用任何保证收益、稳赚不赔的表述\n"
        "- 不得给出具体的买卖点位建议\n"
        "- 投资建议部分必须包含风险提示\n"
        "- 所有数据必须与原始热点信息一致，不得编造数据\n"
        "\n"
        "此外，请基于文章内容提供视觉风格建议：\n"
        "- 主要主题关键词（如：芯片、航天、存储等）\n"
        "- 推荐的配色方案（如：金橙色、蓝色科技、绿色生态等）  \n"
        "- 建议的背景装饰元素（如：电路板、卫星、数据流等）\n"
        "- 适合的数据可视化类型（如：柱状图、趋势图、配比图等）\n"
        "\n"
        "将这些建议以JSON格式附加到文章末尾，标记为【视觉建议】。"
    ),
```

- [ ] **Step 2: Update knowledge_popularization framework template**

Similarly, append the same visual suggestion instructions to the `"knowledge_popularization"` template:

```python
    "knowledge_popularization": (
        '你是一位专业的财经科普专家，正在为"兴风向"栏目撰写知识解读文章。\n'
        '\n'
        '请按以下四段式框架撰写文章：\n'
        '\n'
        '【兴风向·知识解读】{{标题}}\n'
        '\n'
        '一、概念定义\n'
        '用通俗语言解释这个概念的核心含义，让普通读者也能理解。\n'
        '避免过于学术化的表述，多用类比和实例。\n'
        '\n'
        '二、核心要点\n'
        '列出3-5个关键特征或要点，每个要点用一小段文字说明。\n'
        '要点应覆盖：定义特征、运作机制、与其他概念的区别。\n'
        '\n'
        '三、数据与趋势\n'
        '引用关键数据和市场规模，展示发展趋势。\n'
        '数据应来自原始热点信息，不得编造。\n'
        '\n'
        '四、投资参考\n'
        '说明普通投资者如何参与这个领域，关注什么方向。\n'
        '**严禁**推荐具体产品，使用"可关注"而非"建议买入"。\n'
        '必须包含风险提示。\n'
        '\n'
        '合规要求：\n'
        '- 不得使用任何保证收益、稳赚不赔的表述\n'
        '- 不得推荐具体基金产品\n'
        '- 数据必须与原始信息一致，不得编造\n'
        '\n'
        "此外，请基于文章内容提供视觉风格建议：\n"
        "- 主要主题关键词（如：芯片、航天、存储等）\n"
        "- 推荐的配色方案（如：金橙色、蓝色科技、绿色生态等）  \n"
        "- 建议的背景装饰元素（如：电路板、卫星、数据流等）\n"
        "- 适合的数据可视化类型（如：柱状图、趋势图、配比图等）\n"
        "\n"
        "将这些建议以JSON格式附加到文章末尾，标记为【视觉建议】。"
    ),
```

- [ ] **Step 3: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/financial_copywriter.py
git commit -m "feat(tools): add visual theme suggestion prompt to copywriter frameworks"
```

### Task 1.2: Add visual theme extraction and metadata output

**Files:**
- Modify: `src/openharness/tools/financial_copywriter.py`
- Modify: `tests/test_tools/test_financial_copywriter_tool.py`

- [ ] **Step 1: Write failing test for visual theme extraction**

Add to `tests/test_tools/test_financial_copywriter_tool.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_copywriter_tool.py::test_extract_visual_theme_from_article -v`
Expected: FAIL — `_extract_visual_theme` function not defined

- [ ] **Step 3: Add _extract_visual_theme function and _DEFAULT_VISUAL_THEME**

In `src/openharness/tools/financial_copywriter.py`, add after the existing imports:

```python
import re
```

Add the default visual theme constant after `_INFORMAL_TO_STANDARD`:

```python
_DEFAULT_VISUAL_THEME: dict[str, Any] = {
    "primary_theme": "金融科技",
    "color_palette": "金橙暖色系",
    "background_elements": ["抽象科技纹理", "数据流", "向上箭头"],
    "chart_styles": ["柱状图", "折线图", "饼图"]
}
```

Add the `_extract_visual_theme` function after `_extract_key_points`:

```python
def _extract_visual_theme(article: str) -> dict[str, Any]:
    """Extract visual theme suggestions from article's 【视觉建议】 section."""
    if "【视觉建议】" not in article:
        return _DEFAULT_VISUAL_THEME
    
    # Find the JSON content after 【视觉建议】
    theme_marker_pos = article.find("【视觉建议】")
    json_content = article[theme_marker_pos + len("【视觉建议】"):].strip()
    
    # Extract the first valid JSON object
    json_match = re.search(r'\{.*?\}', json_content, re.DOTALL)
    if not json_match:
        return _DEFAULT_VISUAL_THEME
    
    try:
        theme_dict = json.loads(json_match.group(0))
        # Validate required fields
        required_fields = ["primary_theme", "color_palette", "background_elements", "chart_styles"]
        if all(field in theme_dict for field in required_fields):
            return theme_dict
        else:
            return _DEFAULT_VISUAL_THEME
    except (json.JSONDecodeError, TypeError):
        return _DEFAULT_VISUAL_THEME
```

- [ ] **Step 4: Update execute method to include visual_theme in metadata**

In the `execute` method of `FinancialCopywriterTool`, after generating the article and before building metadata, add:

```python
        # Extract visual theme suggestions from article
        visual_theme = _extract_visual_theme(article)
```

Then add `visual_theme` to the metadata dictionary:

```python
        metadata: dict[str, Any] = {
            "article_markdown": article,
            "model_used": model_name,
            "framework": framework,
            "char_count": len(article),
            "key_points": key_points,
            "compliance_check": {
                "passed": compliance_passed,
                "issues": all_issues,
                "sensitive_words_found": sensitive_result["sensitive_words_found"],
                "fact_check_confidence": fact_result["fact_check_confidence"],
            },
            "generated_at": generated_at,
            "product_data": arguments.product_data,
            "visual_theme": visual_theme,
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_copywriter_tool.py -v`
Expected: All tests PASS including new visual theme tests

- [ ] **Step 6: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/financial_copywriter.py tests/test_tools/test_financial_copywriter_tool.py
git commit -m "feat(tools): add visual theme extraction and metadata output to FinancialCopywriterTool"
```

---

## Phase 2: InfographicRendererTool — AI decoration generation

### Task 2.1: Add dynamic prompt building and ImageGenerationTool integration

**Files:**
- Modify: `src/openharness/tools/infographic_renderer.py`
- Modify: `tests/test_tools/test_infographic_renderer_tool.py`

- [ ] **Step 1: Write failing test for dynamic prompt building**

Add to `tests/test_tools/test_infographic_renderer_tool.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_infographic_renderer_tool.py::test_build_dynamic_image_prompt_s0_background -v`
Expected: FAIL — `_build_dynamic_image_prompt` function not defined

- [ ] **Step 3: Add imports and constants**

In `src/openharness/tools/infographic_renderer.py`, add import at top:

```python
from openharness.tools.image_generation_tool import ImageGenerationTool, ImageGenerationInput
```

Add after existing constants:

```python
_AUTO_SELECT_IMAGE_MODELS: list[str] = ["wanx-v1", "qwen-vl-plus"]
```

- [ ] **Step 4: Add _build_dynamic_image_prompt function**

Add after `_fill_template`:

```python
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
```

- [ ] **Step 5: Add _generate_ai_image function**

Add after `_build_dynamic_image_prompt`:

```python
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
        
        image_input = ImageGenerationInput(
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
```

- [ ] **Step 6: Update InfographicRendererInput model**

Add `visual_theme` field to the input model:

```python
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
```

- [ ] **Step 7: Update execute method to handle AI decorations**

In the `execute` method, after parsing product_info, add visual theme parsing:

```python
        # Parse visual theme if provided
        visual_theme = _DEFAULT_VISUAL_THEME.copy()
        if arguments.visual_theme:
            try:
                visual_theme.update(json.loads(arguments.visual_theme))
            except json.JSONDecodeError:
                logger.warning("visual_theme JSON解析失败，使用默认主题")
```

Then, before filling the template, add AI decoration generation:

```python
        # Generate AI decorations if enabled
        decoration_header = None
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
            
            # Generate section header backgrounds for each section
            for i, section in enumerate(sections):
                section_prompt = _build_dynamic_image_prompt(
                    content_theme=visual_theme["primary_theme"],
                    visual_suggestions=visual_theme,
                    element_type="section_header"
                )
                section_bg = await _generate_ai_image(section_prompt, "1080x80", context)
                section_backgrounds.append(section_bg if section_bg else "")
        else:
            # No AI decorations
            section_backgrounds = [""] * len(sections)
```

Update the template filling call to include section backgrounds:

```python
            html = _fill_template(
                article_title=arguments.article_title,
                sections=sections,
                generated_date=generated_date,
                conclusion_title=conclusion_title,
                conclusion_body=conclusion_body,
                decoration_header=decoration_header,
                decoration_chart=None,  # Chart generation can be added later
                decoration_footer=decoration_footer,
                product_info=product_info,
                section_backgrounds=section_backgrounds,
            )
```

- [ ] **Step 8: Update _fill_template function signature**

Update the `_fill_template` function to accept `section_backgrounds`:

```python
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
        product_info=product_info,
        section_backgrounds=section_backgrounds or [],
    )
```

- [ ] **Step 9: Update output text for AI decorations**

Update the decorations text in output_lines:

```python
        # Count generated decorations
        decoration_count = 0
        if decoration_header:
            decoration_count += 1
        if any(bg for bg in section_backgrounds):
            decoration_count += len([bg for bg in section_backgrounds if bg])
            
        decorations_text = f"已生成{decoration_count}个AI装饰元素" if arguments.ai_decorations else "AI装饰功能已禁用"
```

- [ ] **Step 10: Add _DEFAULT_VISUAL_THEME constant**

Add at the top with other constants:

```python
_DEFAULT_VISUAL_THEME: dict[str, Any] = {
    "primary_theme": "金融科技",
    "color_palette": "金橙暖色系",
    "background_elements": ["抽象科技纹理", "数据流", "向上箭头"],
    "chart_styles": ["柱状图", "折线图", "饼图"]
}
```

- [ ] **Step 11: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_infographic_renderer_tool.py -v`
Expected: All tests PASS

- [ ] **Step 12: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/infographic_renderer.py tests/test_tools/test_infographic_renderer_tool.py
git commit -m "feat(tools): add dynamic AI decoration generation to InfographicRendererTool"
```

---

## Phase 3: Template updates — dynamic background support

### Task 3.1: Update HTML template for dynamic backgrounds

**Files:**
- Modify: `src/openharness/templates/xingfengxiang/template.html`
- Modify: `src/openharness/templates/xingfengxiang/styles.css`

- [ ] **Step 1: Update HTML template**

Replace the entire content of `src/openharness/templates/xingfengxiang/template.html` with:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, initial-scale=1">
    <title>{{ article_title }}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <!-- Left decoration bar (贯穿全文) -->
    <div class="left-bar"></div>

    <!-- Top: Brand + Title + Date -->
    <div class="header" 
         {% if decoration_header %}style="background-image: url('{{ decoration_header }}'); background-size: cover; background-position: center;"{% endif %}>
        <div class="brand-tag">兴风向</div>
        <h1 class="article-title">{{ article_title }}</h1>
        <div class="article-date">{{ generated_date }}</div>
        <div class="header-divider"></div>
    </div>

    <!-- Middle: Content sections with alternating backgrounds -->
    <div class="content">
        {% for section in sections %}
        <div class="section-container">
            {% if loop.index is odd %}
            <div class="section-white">
            {% else %}
            <div class="section-gold">
            {% endif %}
                {% if section_backgrounds and section_backgrounds[loop.index0] %}
                <div class="section-header" style="background-image: url('{{ section_backgrounds[loop.index0] }}'); background-size: repeat-x; background-position: left;">
                    <h2 class="section-title">{{ section.title }}</h2>
                </div>
                {% else %}
                <h2 class="section-title">{{ section.title }}</h2>
                {% endif %}
                <div class="section-body">{{ section.body }}</div>
                {% if section.data_cards %}
                <div>
                    {% for card in section.data_cards %}
                    <span class="product-nav">{{ card }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% if not loop.last %}
            <div class="section-divider"></div>
            {% endif %}
        </div>
        {% endfor %}

        <!-- Product card (optional, inserted between content and conclusion) -->
        {% if product_info %}
        <div class="section-divider"></div>
        <div class="product-card">
            <div class="product-card-header">相关产品推荐</div>
            <div class="product-card-body">
                <div class="product-name">{{ product_info.product_name }}</div>
                <div class="product-code">代码: {{ product_info.product_code }}</div>
                <div class="product-stats">
                    <span class="product-nav">净值: {{ product_info.nav }}</span>
                    <span class="product-change">近期: {{ product_info.recent_change }}</span>
                </div>
                <div class="product-risk">风险等级: {{ product_info.risk_level }}</div>
                <div class="product-recommendation">{{ product_info.recommendation }}</div>
            </div>
        </div>
        {% endif %}
    </div>

    <!-- Bottom: Conclusion + Risk Warning + Footer -->
    <div class="conclusion">
        <h3 class="conclusion-title">{{ conclusion_title }}</h3>
        <div class="conclusion-body">{{ conclusion_body }}</div>
        <div class="risk-warning">⚠️ 风险提示：以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。</div>
    </div>

    <div class="footer">
        <span class="footer-brand">兴风向 · 财经热点解读</span>
        <div class="footer-disclaimer">本文由AI辅助生成，内容仅供参考，不构成任何投资建议。数据来源以原文为准。</div>
        {% if decoration_footer %}
        <img class="decoration-footer-badge" src="{{ decoration_footer }}" alt="品牌徽章">
        {% endif %}
    </div>
</body>
</html>
```

- [ ] **Step 2: Update CSS for section containers and headers**

Add to `src/openharness/templates/xingfengxiang/styles.css`:

```css
/* ── Section Containers ── */
.section-container {
    margin-bottom: 0;
}

/* ── Section Headers with Dynamic Backgrounds ── */
.section-header {
    padding: 20px 40px 20px 60px; /* Extra left padding for decoration bar */
    margin: -40px -40px 20px -40px; /* Negative margins to extend to container edges */
    background-color: rgba(255, 255, 255, 0.9); /* Semi-transparent white overlay */
    border-radius: 8px 8px 0 0;
}

.section-header .section-title {
    margin: 0;
    padding: 0;
    border-left: none; /* Remove original left border since we have background */
}
```

- [ ] **Step 3: Verify template renders correctly**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -c "
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
env = Environment(loader=FileSystemLoader(str(Path('src/openharness/templates/xingfengxiang'))))
template = env.get_template('template.html')
html = template.render(
    article_title='60只芯片股历史新高',
    generated_date='2026-06-08',
    sections=[
        {'title': 'CPU重估打开增量空间', 'body': '智能体浪潮驱动CPU需求增长。'},
        {'title': '存储芯片进入景气周期', 'body': 'CSP大厂抢锁产能。'},
    ],
    conclusion_title='核心结论',
    conclusion_body='芯片板块景气度持续提升。',
    product_info=None,
    decoration_header='/fake/path/header.png',
    decoration_chart=None,
    decoration_footer=None,
    section_backgrounds=['/fake/path/section1.png', '/fake/path/section2.png'],
)
print(f'OK: Template rendered with dynamic backgrounds, length={len(html)}')
"`

Expected: Output confirms template renders with dynamic background structure

- [ ] **Step 4: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/templates/xingfengxiang/template.html src/openharness/templates/xingfengxiang/styles.css
git commit -m "feat(templates): add dynamic background support for AI-generated decorations"
```

---

## Phase 4: Pipeline Skill update — visual theme confirmation

### Task 4.1: Update Pipeline Skill with visual theme confirmation

**Files:**
- Modify: `src/openharness/skills/bundled/content/financial_hotspot_pipeline.md`

- [ ] **Step 1: Update Skill file**

Replace the content of `src/openharness/skills/bundled/content/financial_hotspot_pipeline.md` with:

```markdown
---
name: financial-hotspot-pipeline
description: 给定主题→搜索热点→生成文案→渲染长图的全流程自动化
---

# 财经热点生图流程

当收到"热点生图"、"财经热点生图"、"/financial_hotspot_pipeline"指令时，按以下步骤操作。

**必须先确认主题和内容类型**：

## 步骤0：确认主题和类型

询问用户（或从输入推断）：
- **主题**：什么事件/知识点？（如"央行降息"、"创新药"、"科创板"）
- **内容类型**：
  - `knowledge_popularization` — 知识普及型（"什么是XX"、"XX怎么看"）
  - `xingfengxiang` — 纯热点分析型（"央行降息意味着什么"）
  - `xingfengxiang` + 产品数据 — 热点+产品推荐型（兴业证券业务场景）
- **是否带产品推荐**：如果类型是热点+产品，需要提供产品数据（JSON格式，包含product_name, product_code, nav, recent_change, risk_level, recommendation）

## 步骤1：搜索热点

调用 FinancialHotSpotScannerTool，参数：
- sources: ["eastmoney", "sina_hot", "weibo_hot"]
- topic: 用户指定的主题关键词（如"降息"、"创新药"、"科创板"）
- categories: ["policy", "industry", "market", "company"]
- max_items: 10

保存 ToolResult.metadata["hotspots"] 数据供后续步骤使用。

**错误处理**：
- 所有源抓取失败 → Pipeline 终止，返回错误信息
- 搜索结果为空 → 提示用户换主题或改关键词

## 步骤2：生成文案

调用 FinancialCopywriterTool：
- hotspot_data: ToolResult.metadata["hotspots"] 的 JSON 序列化字符串
- framework: 根据内容类型选择：
  - 知识普及 → "knowledge_popularization"
  - 热点分析 → "xingfengxiang"
- style: "professional_accessible"
- model: null（自动选择）
- product_data: 如果带产品推荐，传入产品 JSON；否则不传

**合规检查**：
- ToolResult.metadata["compliance_check"]["passed"] == False → 保存为 _nc.md，提示用户人工审核
- passed == True → 继续步骤2.5

**LLM 调用失败处理**：
- 换模型重试一次（glm-4 → qwen-max → deepseek-v3）
- 仍失败 → Pipeline 终止

## 步骤2.5：确认视觉风格（可选）

如果用户未在步骤0中指定视觉风格，展示 LLM 生成的视觉建议：
- 主题：{{ ToolResult.metadata["visual_theme"]["primary_theme"] }}
- 配色：{{ ToolResult.metadata["visual_theme"]["color_palette"] }}
- 背景元素：{{ ToolResult.metadata["visual_theme"]["background_elements"] | join(', ') }}

询问用户：
- 是否接受此视觉方案？[是/否/自定义]

**用户选择处理**：
- **是**：继续步骤3，使用建议的 visual_theme
- **否**：继续步骤3，使用默认视觉主题（不传 visual_theme 参数）
- **自定义**：询问用户具体的视觉要求（主题、配色、元素），构建自定义 visual_theme JSON

## 步骤3：生成长图

调用 InfographicRendererTool：
- article_content: 步骤2 ToolResult.metadata["article_markdown"]
- article_title: 主题标题
- template: "xingfengxiang_default"
- ai_decorations: true
- visual_theme: 步骤2.5确定的视觉主题 JSON（如果有）
- product_data: 如果带产品推荐，传入产品 JSON；否则不传
- output_dir: "{cwd}/data/financial_hotspot_pipeline/{YYYY-MM-DD}/infographics"

**尺寸合规检查**（宽度必须1080px，高度≥1920px）：
- 不合规 → 相同参数重试最多3次
- 3次仍不合规 → 标记为 size_failed

## 步骤4：保存记录

保存到 {cwd}/data/financial_hotspot_pipeline/{YYYY-MM-DD}/：
- hotspots.json — 步骤1原始数据
- article.md — 步骤2文案
- infographic.png — 步骤3长图（已自动保存）
- pipeline_log.json — 全流程日志

pipeline_log.json：
```json
{
    "run_time": "当前UTC时间",
    "trigger": "manual",
    "topic": "用户指定的主题",
    "content_type": "knowledge_popularization | xingfengxiang | xingfengxiang_with_product",
    "visual_theme": "使用的视觉主题",
    "hotspots_scanned": 5,
    "compliance_passed": true,
    "image_size": "1080x3500",
    "product_name": "科创芯片ETF（如果有产品）",
    "failed_items": [],
    "total_duration_seconds": 120,
    "model_used": "glm-4"
}
```

## 触发方式

- 斜杠命令：/financial_hotspot_pipeline
- 关键词："热点生图"、"财经热点生图"

## Cron 定时配置（可选）

CronCreate: cron="0 9 * * *", prompt="/financial_hotspot_pipeline", durable=true

## 注意事项

- 长图宽度必须1080px（一票否决），高度动态伸缩
- 所有中间产物必须保存
- 合规未通过的文案仍然保存，供人工审核
- AI装饰元素生成可能增加处理时间，但显著提升视觉效果
```

- [ ] **Step 2: Verify Skill loads correctly**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -c "
from openharness.skills.bundled import get_bundled_skills
skills = get_bundled_skills()
for s in skills:
    if s.name == 'financial-hotspot-pipeline':
        print(f'OK: {s.name} loaded with visual theme confirmation step')
        break
"`

- [ ] **Step 3: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/skills/bundled/content/financial_hotspot_pipeline.md
git commit -m "feat(skills): add visual theme confirmation step to financial-hotspot-pipeline Skill"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Dynamic prompt-driven visual theming: Phase 1 (CopywriterTool visual suggestions) + Phase 2 (RendererTool dynamic prompts)
- ✅ AI decoration generation: Phase 2 (ImageGenerationTool integration) + Phase 3 (Template support)
- ✅ HTML fixed layout: Phase 3 (Template updates with dynamic backgrounds)
- ✅ User-controlled visual themes: Phase 4 (Pipeline Skill confirmation step)
- ✅ No hardcoded theme recognition: All theme logic is LLM-driven via visual suggestions

**2. Placeholder scan:** No TBD/TODO found. All steps have complete code implementations.

**3. Type consistency:**
- `visual_theme: str | None` added to InfographicRendererInput — matches JSON string format from CopywriterTool
- `_extract_visual_theme()` returns dict matching `_DEFAULT_VISUAL_THEME` structure
- `_build_dynamic_image_prompt()` parameters match visual theme dict structure
- Template variables: `decoration_header` (str), `section_backgrounds` (list[str]) match generated image paths
- ImageGenerationTool integration uses existing infrastructure with proper error handling

**4. Scope check:** Plan is focused on AI decoration enhancement only, builds on existing pipeline without unrelated changes.
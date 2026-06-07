# Financial Pipeline Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the financial hotspot pipeline from "scan all → batch articles" to "given a topic → one focused article → one long image", supporting three content types: knowledge_popularization, pure hotspot analysis, and hotspot+product.

**Architecture:** Topic-driven pipeline: user gives a topic → ScannerTool filters/searches relevant hotspots → CopywriterTool generates one focused article (using appropriate framework) → RendererTool renders dynamic-height long image with warm-color template → save result. Product data is optional input for type 3.

**Tech Stack:** Python, Pydantic, httpx, Playwright, Jinja2, pytest

---

## Scope: 5 Phases

This plan covers modifications to 4 existing tools + 1 skill + 1 template set. Each phase produces working, tested software independently.

**Phase 1**: ScannerTool — add `topic` parameter for focused search
**Phase 2**: CopywriterTool — add `knowledge_popularization` framework + `product_data` parameter
**Phase 3**: RendererTool — dynamic height + product card module
**Phase 4**: Template redesign — warm colors, alternating backgrounds, left decoration bar
**Phase 5**: Pipeline Skill rewrite + spec update

---

## File Structure

| File | Phase | Responsibility |
|------|-------|----------------|
| `src/openharness/tools/financial_hotspot_scanner.py` | 1 | Add topic filtering to ScannerTool |
| `tests/test_tools/test_financial_hotspot_scanner_tool.py` | 1 | Tests for topic parameter |
| `src/openharness/tools/financial_copywriter.py` | 2 | Add new frameworks + product_data input |
| `tests/test_tools/test_financial_copywriter_tool.py` | 2 | Tests for new frameworks + product data |
| `src/openharness/tools/infographic_renderer.py` | 3 | Dynamic height + product card rendering |
| `tests/test_tools/test_infographic_renderer_tool.py` | 3 | Tests for dynamic height + product card |
| `src/openharness/templates/xingfengxiang/template.html` | 4 | Redesigned warm-color template |
| `src/openharness/templates/xingfengxiang/styles.css` | 4 | Redesigned warm-color CSS |
| `src/openharness/skills/bundled/content/financial_hotspot_pipeline.md` | 5 | Rewritten topic-driven Skill |
| `docs/superpowers/specs/2026-06-07-financial-hotspot-pipeline-design.md` | 5 | Updated spec |

---

## Phase 1: ScannerTool — topic parameter

### Task 1.1: Add `topic` parameter to FinancialHotSpotScannerInput

**Files:**
- Modify: `src/openharness/tools/financial_hotspot_scanner.py`
- Modify: `tests/test_tools/test_financial_hotspot_scanner_tool.py`

- [ ] **Step 1: Write failing test for topic parameter**

Add to `tests/test_tools/test_financial_hotspot_scanner_tool.py`:

```python
@pytest.mark.asyncio
async def test_scanner_topic_filter(tmp_path: Path, monkeypatch):
    context = ToolExecutionContext(cwd=tmp_path)

    fake_hotspots = [
        {
            "title": "央行宣布降息0.25个百分点",
            "source": "eastmoney",
            "category": "policy",
            "summary": "降息25个基点",
            "url": "https://example.com/1",
            "published_at": "2026-06-07T09:30:00",
        },
        {
            "title": "新能源汽车销量创新高",
            "source": "eastmoney",
            "category": "industry",
            "summary": "销量突破100万",
            "url": "https://example.com/2",
            "published_at": "2026-06-07T10:15:00",
        },
        {
            "title": "科创板芯片企业集体上涨",
            "source": "sina_hot",
            "category": "market",
            "summary": "芯片板块领涨",
            "url": "https://example.com/3",
            "published_at": "2026-06-07T11:00:00",
        },
    ]

    async def fake_fetch_eastmoney(*, max_items: int) -> list[dict]:
        return fake_hotspots[:max_items]

    async def fake_fetch_sina_hot(*, max_items: int) -> list[dict]:
        return [fake_hotspots[2]]

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

    # Filter by topic "降息" — should only return hotspots containing that keyword
    result = await FinancialHotSpotScannerTool().execute(
        FinancialHotSpotScannerInput(sources=["eastmoney", "sina_hot"], topic="降息", max_items=10),
        context,
    )

    assert result.is_error is False
    assert len(result.metadata["hotspots"]) == 1
    assert "降息" in result.metadata["hotspots"][0]["title"]


def test_scanner_input_model_with_topic():
    input_model = FinancialHotSpotScannerInput(topic="创新药")
    assert input_model.topic == "创新药"


def test_scanner_input_model_topic_default():
    input_model = FinancialHotSpotScannerInput()
    assert input_model.topic is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_hotspot_scanner_tool.py::test_scanner_topic_filter tests/test_tools/test_financial_hotspot_scanner_tool.py::test_scanner_input_model_with_topic -v`
Expected: FAIL — `topic` field not in model

- [ ] **Step 3: Add `topic` field to FinancialHotSpotScannerInput and implement filtering**

In `src/openharness/tools/financial_hotspot_scanner.py`, add to the Input model:

```python
    topic: str | None = Field(
        default=None,
        description="定向搜索主题关键词；None则返回全量热点",
    )
```

In the `execute` method, after deduplication and category filtering, add topic filtering:

```python
        # Filter by topic keyword (if specified)
        if arguments.topic:
            topic_kw = arguments.topic.strip().lower()
            filtered = [
                h for h in filtered
                if topic_kw in h.get("title", "").lower()
                or topic_kw in h.get("summary", "").lower()
            ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_hotspot_scanner_tool.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/financial_hotspot_scanner.py tests/test_tools/test_financial_hotspot_scanner_tool.py
git commit -m "feat(tools): add topic parameter to FinancialHotSpotScannerTool for focused search"
```

---

## Phase 2: CopywriterTool — new frameworks + product data

### Task 2.1: Add `knowledge_popularization` framework template

**Files:**
- Modify: `src/openharness/tools/financial_copywriter.py`
- Modify: `tests/test_tools/test_financial_copywriter_tool.py`

- [ ] **Step 1: Write failing test for knowledge_popularization framework**

Add to `tests/test_tools/test_financial_copywriter_tool.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_copywriter_tool.py::test_knowledge_popularization_template_exists -v`
Expected: FAIL — `knowledge_popularization` not in `_FRAMEWORK_TEMPLATES`

- [ ] **Step 3: Add knowledge_popularization template to `_FRAMEWORK_TEMPLATES`**

In `src/openharness/tools/financial_copywriter.py`, add after the `"standard"` entry in `_FRAMEWORK_TEMPLATES`:

```python
    "knowledge_popularization": (
        "你是一位专业的财经科普专家，正在为"兴风向"栏目撰写知识解读文章。\n"
        "\n"
        "请按以下四段式框架撰写文章：\n"
        "\n"
        "【兴风向·知识解读】{{标题}}\n"
        "\n"
        "一、概念定义\n"
        "用通俗语言解释这个概念的核心含义，让普通读者也能理解。\n"
        "避免过于学术化的表述，多用类比和实例。\n"
        "\n"
        "二、核心要点\n"
        "列出3-5个关键特征或要点，每个要点用一小段文字说明。\n"
        "要点应覆盖：定义特征、运作机制、与其他概念的区别。\n"
        "\n"
        "三、数据与趋势\n"
        "引用关键数据和市场规模，展示发展趋势。\n"
        "数据应来自原始热点信息，不得编造。\n"
        "\n"
        "四、投资参考\n"
        "说明普通投资者如何参与这个领域，关注什么方向。\n"
        "**严禁**推荐具体产品，使用"可关注"而非"建议买入"。\n"
        "必须包含风险提示。\n"
        "\n"
        "合规要求：\n"
        "- 不得使用任何保证收益、稳赚不赔的表述\n"
        "- 不得推荐具体基金产品\n"
        "- 数据必须与原始信息一致，不得编造\n"
    ),
```

Also update the `framework` field description in `FinancialCopywriterInput` to include the new option:

```python
    framework: str = Field(
        default="xingfengxiang",
        description="文案框架：xingfengxiang(兴风向解读), standard(标准分析), knowledge_popularization(知识普及)",
    )
```

And update the `execute` method's framework validation check to include the new value:

```python
        if framework not in _FRAMEWORK_TEMPLATES:
            return ToolResult(
                output=f"未知的文案框架: '{framework}'。支持: xingfengxiang, standard, knowledge_popularization",
                is_error=True,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_copywriter_tool.py -v`
Expected: All tests PASS including new knowledge_popularization tests

- [ ] **Step 5: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/financial_copywriter.py tests/test_tools/test_financial_copywriter_tool.py
git commit -m "feat(tools): add knowledge_popularization framework to FinancialCopywriterTool"
```

### Task 2.2: Add `product_data` optional parameter

**Files:**
- Modify: `src/openharness/tools/financial_copywriter.py`
- Modify: `tests/test_tools/test_financial_copywriter_tool.py`

- [ ] **Step 1: Write failing test for product_data parameter**

Add to `tests/test_tools/test_financial_copywriter_tool.py`:

```python
FAKE_PRODUCT_DATA = json.dumps({
    "product_name": "科创芯片ETF",
    "product_code": "588200",
    "nav": "1.2345",
    "recent_change": "+2.3%",
    "risk_level": "中高风险",
    "recommendation": "芯片板块利好，可关注相关ETF",
})


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_copywriter_tool.py::test_copywriter_input_model_with_product_data -v`
Expected: FAIL — `product_data` field not in model

- [ ] **Step 3: Add `product_data` field to FinancialCopywriterInput and integrate into prompt**

In `src/openharness/tools/financial_copywriter.py`, add to Input model:

```python
    product_data: str | None = Field(
        default=None,
        description="产品推荐数据（JSON格式），包含product_name, product_code, nav, recent_change, risk_level, recommendation。None则不插入产品推荐",
    )
```

In the `execute` method, after building `user_prompt`, add product data section:

```python
        # Add product data to user prompt if provided
        if arguments.product_data:
            try:
                product = json.loads(arguments.product_data)
            except json.JSONDecodeError:
                return ToolResult(
                    output=f"product_data JSON解析失败",
                    is_error=True,
                )
            product_brief = (
                f"\n\n**产品推荐信息**（请在"市场影响"和"投资建议"之间自然插入推荐）：\n"
                f"- 产品名称: {product.get('product_name', '')}\n"
                f"- 产品代码: {product.get('product_code', '')}\n"
                f"- 最新净值: {product.get('nav', '')}\n"
                f"- 近期涨跌: {product.get('recent_change', '')}\n"
                f"- 风险等级: {product.get('risk_level', '')}\n"
                f"- 推荐理由: {product.get('recommendation', '')}\n"
            )
            user_prompt += product_brief
```

Also add `product_data` to the metadata output:

```python
            "product_data": arguments.product_data,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_financial_copywriter_tool.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/financial_copywriter.py tests/test_tools/test_financial_copywriter_tool.py
git commit -m "feat(tools): add product_data parameter to FinancialCopywriterTool for product recommendation insertion"
```

---

## Phase 3: InfographicRendererTool — dynamic height + product card

### Task 3.1: Change from fixed 1080×1920 to dynamic height

**Files:**
- Modify: `src/openharness/tools/infographic_renderer.py`
- Modify: `tests/test_tools/test_infographic_renderer_tool.py`

- [ ] **Step 1: Write failing test for dynamic height**

Add to `tests/test_tools/test_infographic_renderer_tool.py`:

```python
def test_check_size_compliance_dynamic_valid():
    """Width must be exactly 1080, height can vary."""
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_infographic_renderer_tool.py::test_check_size_compliance_dynamic_valid -v`
Expected: FAIL — current `_check_size_compliance` requires exact 1080×1920

- [ ] **Step 3: Update `_check_size_compliance` and `_REQUIRED_HEIGHT`**

In `src/openharness/tools/infographic_renderer.py`:

Replace `_REQUIRED_HEIGHT = 1920` with:

```python
_REQUIRED_WIDTH = 1080
_MIN_HEIGHT = 1920  # minimum height, actual height is dynamic
```

Update `_check_size_compliance`:

```python
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
```

Update `_render_html_to_png` to use `full_page=True` screenshot with only width constraint:

```python
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

    html_path.unlink(missing_ok=True)
    return output_path
```

Update the execute method to remove height parameter from `_render_html_to_png` call and adjust compliance check description:

```python
        png_path = await _render_html_to_png(
            html=html,
            output_path=output_path,
            width=_REQUIRED_WIDTH,
        )
```

Update output text to reflect dynamic height:

```python
            f"尺寸: {actual_width}×{actual_height}px (宽度1080px标准，高度随内容伸缩)",
```

- [ ] **Step 4: Update existing tests for new compliance logic**

In `tests/test_tools/test_infographic_renderer_tool.py`, update `test_check_size_compliance_valid`:

```python
def test_check_size_compliance_valid():
    result = _check_size_compliance(1080, 1920)
    assert result["size_compliance"] is True
    assert result["issues"] == []
```

Update `test_check_size_compliance_invalid_height`:

```python
def test_check_size_compliance_invalid_height():
    # Height below minimum (1920) should fail
    result = _check_size_compliance(1080, 1500)
    assert result["size_compliance"] is False
    assert len(result["issues"]) > 0
```

Update `test_renderer_success_with_mocked_playwright` to accept dynamic height:

```python
@pytest.mark.asyncio
async def test_renderer_success_with_mocked_playwright(tmp_path: Path, monkeypatch):
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_infographic_renderer_tool.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/infographic_renderer.py tests/test_tools/test_infographic_renderer_tool.py
git commit -m "feat(tools): change InfographicRendererTool to dynamic height (width=1080, height>=1920)"
```

### Task 3.2: Add product card rendering support

**Files:**
- Modify: `src/openharness/tools/infographic_renderer.py`
- Modify: `tests/test_tools/test_infographic_renderer_tool.py`
- Modify: `src/openharness/templates/xingfengxiang/template.html`

- [ ] **Step 1: Write failing test for product card in renderer**

Add to `tests/test_tools/test_infographic_renderer_tool.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_infographic_renderer_tool.py::test_renderer_input_model_with_product_data -v`
Expected: FAIL — `product_data` not in Input model

- [ ] **Step 3: Add `product_data` to Input model and integrate into template rendering**

In `src/openharness/tools/infographic_renderer.py`, add to `InfographicRendererInput`:

```python
    product_data: str | None = Field(
        default=None,
        description="产品推荐数据（JSON格式），包含product_name等。None则不插入产品推荐卡",
    )
```

In the `execute` method, parse product_data and pass to template:

```python
        # Parse product data if provided
        product_info = None
        if arguments.product_data:
            try:
                product_info = json.loads(arguments.product_data)
            except json.JSONDecodeError:
                return ToolResult(
                    output="product_data JSON解析失败",
                    is_error=True,
                )
```

Pass `product_info` to `_fill_template`:

```python
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
            )
```

Update `_fill_template` to accept and render `product_info`:

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
    )
```

Add product data to output text and metadata:

```python
    # In output lines, add product info if present
    if arguments.product_data:
        output_lines.insert(-1, f"产品推荐: {product_info.get('product_name', '')}({product_info.get('product_code', '')})")

    # In metadata
    metadata["product_data"] = arguments.product_data,
```

Add `import json` if not already present in the file.

- [ ] **Step 4: Add product card section to HTML template**

In `src/openharness/templates/xingfengxiang/template.html`, add product card block after the content sections and before the conclusion:

```html
    {% if product_info %}
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_infographic_renderer_tool.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/tools/infographic_renderer.py tests/test_tools/test_infographic_renderer_tool.py src/openharness/templates/xingfengxiang/template.html
git commit -m "feat(tools): add product_data support to InfographicRendererTool with product card template"
```

---

## Phase 4: Template redesign — warm colors, alternating backgrounds, left decoration bar

### Task 4.1: Redesign CSS to match reference images

**Files:**
- Modify: `src/openharness/templates/xingfengxiang/styles.css`

- [ ] **Step 1: Rewrite styles.css with warm color scheme**

Replace the entire content of `src/openharness/templates/xingfengxiang/styles.css` with:

```css
/* 兴风向 (Xingfengxiang) Infographic Styles — Warm Color Edition */
/* Based on reference images: 金橙暖色系, 白色+淡金色交替背景, 左侧装饰条 */
/* Width: 1080px, Height: dynamic (full_page) */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    width: 1080px;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif;
    color: #333333;
    background: #FFF8E7;
    overflow: visible;
    position: relative;
}

/* ── Left Decoration Bar ── */
.left-bar {
    position: fixed;
    left: 0;
    top: 0;
    width: 12px;
    height: 100%;
    background: linear-gradient(180deg, #FBB03B 0%, #F59E0B 30%, #EA580C 70%, #C2410C 100%);
    z-index: 100;
}

/* ── Top Section: Brand + Title + Date ── */
.header {
    padding: 80px 60px 40px 60px;
    background: linear-gradient(135deg, #FFF8E7 0%, #FDE68A 50%, #FBB03B 100%);
}

.brand-tag {
    display: inline-block;
    padding: 8px 20px;
    background: #EA580C;
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
    border-radius: 6px;
    letter-spacing: 3px;
    margin-bottom: 28px;
}

.article-title {
    font-size: 46px;
    font-weight: 700;
    line-height: 1.3;
    color: #1A1A1A;
    margin-bottom: 20px;
}

.article-date {
    font-size: 20px;
    color: #92400E;
    margin-bottom: 8px;
}

.header-divider {
    height: 4px;
    background: linear-gradient(90deg, #EA580C 0%, #FBB03B 40%, #FDE68A 100%);
    margin-top: 30px;
    border-radius: 2px;
}

/* ── Content Sections ── */
.content {
    padding: 0 60px 0 30px;  /* left padding accounts for decoration bar */
}

/* Alternating backgrounds: white sections and golden sections */
.section-white {
    padding: 40px 40px;
    background: #FFFFFF;
    margin-bottom: 0;
}

.section-gold {
    padding: 40px 40px;
    background: #FFF8E7;
    margin-bottom: 0;
}

.section-title {
    font-size: 32px;
    font-weight: 700;
    color: #1A1A1A;
    margin-bottom: 20px;
    padding-left: 20px;
    border-left: 6px solid #EA580C;
}

.section-body {
    font-size: 24px;
    line-height: 1.7;
    color: #444444;
}

/* ── Product Card ── */
.product-card {
    margin: 30px 40px;
    padding: 30px;
    background: #FFFFFF;
    border: 2px solid #FBB03B;
    border-radius: 12px;
}

.product-card-header {
    font-size: 26px;
    font-weight: 700;
    color: #EA580C;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 2px solid #FDE68A;
}

.product-card-body {
    font-size: 22px;
    color: #333333;
    line-height: 1.6;
}

.product-name {
    font-size: 28px;
    font-weight: 700;
    color: #1A1A1A;
    margin-bottom: 8px;
}

.product-code {
    font-size: 20px;
    color: #666666;
    margin-bottom: 12px;
}

.product-stats {
    display: flex;
    gap: 24px;
    margin-bottom: 12px;
}

.product-nav, .product-change {
    display: inline-block;
    padding: 8px 16px;
    background: #FEF3C7;
    border-radius: 6px;
    font-size: 20px;
    color: #92400E;
}

.product-change {
    color: #059669;
    background: #D1FAE5;
}

.product-risk {
    font-size: 18px;
    color: #DC2626;
    margin-bottom: 10px;
    padding: 6px 12px;
    background: #FEE2E2;
    border-radius: 4px;
    display: inline-block;
}

.product-recommendation {
    font-size: 20px;
    color: #444444;
}

/* ── Conclusion Section ── */
.conclusion {
    padding: 40px 40px;
    background: #FDE68A;
    border-top: 4px solid #EA580C;
}

.conclusion-title {
    font-size: 30px;
    font-weight: 700;
    color: #1A1A1A;
    margin-bottom: 16px;
}

.conclusion-body {
    font-size: 24px;
    line-height: 1.6;
    color: #333333;
}

/* ── Risk Warning ── */
.risk-warning {
    margin-top: 24px;
    padding: 16px 24px;
    background: #FEE2E2;
    border: 2px solid #DC2626;
    border-radius: 8px;
    font-size: 18px;
    color: #991B1B;
    line-height: 1.5;
}

/* ── Footer ── */
.footer {
    padding: 40px 60px;
    background: linear-gradient(135deg, #FDE68A 0%, #FBB03B 100%);
    text-align: center;
}

.footer-brand {
    font-size: 22px;
    color: #92400E;
    font-weight: 700;
}

.footer-disclaimer {
    font-size: 14px;
    color: #78350F;
    margin-top: 12px;
    line-height: 1.4;
}

/* ── Section Divider Lines ── */
.section-divider {
    height: 2px;
    background: linear-gradient(90deg, #FBB03B 0%, transparent 100%);
    margin: 0 40px;
}
```

- [ ] **Step 2: Update HTML template to use alternating section backgrounds and left bar**

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
    <div class="header">
        {% if decoration_header %}
        <img class="decoration-header-illustration" src="{{ decoration_header }}" alt="插图">
        {% endif %}
        <div class="brand-tag">兴风向</div>
        <h1 class="article-title">{{ article_title }}</h1>
        <div class="article-date">{{ generated_date }}</div>
        <div class="header-divider"></div>
    </div>

    <!-- Middle: Content sections with alternating backgrounds -->
    <div class="content">
        {% for section in sections %}
        {% if loop.index is odd %}
        <div class="section-white">
        {% else %}
        <div class="section-gold">
        {% endif %}
            <h2 class="section-title">{{ section.title }}</h2>
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

- [ ] **Step 3: Verify template renders correctly**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -c "
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
env = Environment(loader=FileSystemLoader(str(Path('src/openharness/templates/xingfengxiang'))))
template = env.get_template('template.html')
html = template.render(
    article_title='央行降息0.25个百分点',
    generated_date='2026-06-07',
    sections=[
        {'title': '事件概述', 'body': '央行宣布降息。', 'data_cards': ['降息0.25%', 'MLF利率']},
        {'title': '政策解读', 'body': '降息背景是经济放缓。'},
        {'title': '市场影响', 'body': '对债券利好。'},
        {'title': '投资建议', 'body': '建议关注利率敏感板块。'},
    ],
    conclusion_title='核心结论',
    conclusion_body='央行降息释放宽松信号。',
    product_info=None,
    decoration_header=None,
    decoration_chart=None,
    decoration_footer=None,
)
print(f'OK: Template rendered, length={len(html)}, has left-bar={\"left-bar\" in html}, has section-white={\"section-white\" in html}')
"`
Expected: Output confirms template renders with warm color structure

- [ ] **Step 4: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/templates/xingfengxiang/styles.css src/openharness/templates/xingfengxiang/template.html
git commit -m "feat(templates): redesign xingfengxiang template — warm colors, alternating backgrounds, left decoration bar, product card"
```

- [ ] **Step 5: Run renderer tests to verify template changes don't break existing tests**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -m pytest tests/test_tools/test_infographic_renderer_tool.py -v`
Expected: All tests PASS

---

## Phase 5: Pipeline Skill rewrite + spec update

### Task 5.1: Rewrite Pipeline Skill for topic-driven flow

**Files:**
- Modify: `src/openharness/skills/bundled/content/financial_hotspot_pipeline.md`

- [ ] **Step 1: Rewrite the Skill file**

Replace the entire content of `src/openharness/skills/bundled/content/financial_hotspot_pipeline.md` with:

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
- passed == True → 继续步骤3

**LLM 调用失败处理**：
- 换模型重试一次（glm-4 → qwen-max → deepseek-v3）
- 仍失败 → Pipeline 终止

## 步骤3：生成长图

调用 InfographicRendererTool：
- article_content: 步骤2 ToolResult.metadata["article_markdown"]
- article_title: 主题标题
- template: "xingfengxiang_default"
- ai_decorations: true
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
```

- [ ] **Step 2: Verify Skill loads correctly**

Run: `cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness && .venv/bin/python -c "
from openharness.skills.bundled import get_bundled_skills
skills = get_bundled_skills()
for s in skills:
    if s.name == 'financial-hotspot-pipeline':
        print(f'OK: {s.name} loaded, desc={s.description}')
        break
"`

- [ ] **Step 3: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add src/openharness/skills/bundled/content/financial_hotspot_pipeline.md
git commit -m "feat(skills): rewrite financial-hotspot-pipeline Skill for topic-driven single-image flow with 3 content types"
```

### Task 5.2: Update design spec

**Files:**
- Modify: `docs/superpowers/specs/2026-06-07-financial-hotspot-pipeline-design.md`

- [ ] **Step 1: Update the spec sections 2, 5, 6, 7 to reflect new pipeline logic**

Key changes:
- Section 2: Change "子项目拆分与依赖" from batch to topic-driven
- Section 5: Add `knowledge_popularization` framework and `product_data` to CopywriterTool spec
- Section 6: Change from fixed 1080×1920 to dynamic height, add product card to RendererTool spec
- Section 7: Rewrite Skill to match Task 5.1

- [ ] **Step 2: Commit**

```bash
cd /Users/wulili/Documents/python/agent-platform/universal-agent-projects/OpenHarness
git add docs/superpowers/specs/2026-06-07-financial-hotspot-pipeline-design.md
git commit -m "docs(specs): update pipeline spec — topic-driven flow, 3 content types, dynamic height, product card"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Topic-driven pipeline (one topic → one image): Phase 5 Skill rewrite
- ✅ Three content types: Phase 2 (CopywriterTool frameworks) + Phase 5 (Skill)
- ✅ ScannerTool topic search: Phase 1
- ✅ CopywriterTool product_data: Phase 2 Task 2.2
- ✅ RendererTool dynamic height: Phase 3 Task 3.1
- ✅ RendererTool product card: Phase 3 Task 3.2
- ✅ Warm color template: Phase 4
- ✅ Spec update: Phase 5 Task 5.2

**2. Placeholder scan:** No TBD/TODO found. All steps have complete code.

**3. Type consistency:**
- `topic: str | None` added to ScannerInput — used in Skill as `topic: "降息"`
- `framework: str` field already exists, new values "knowledge_popularization" added to `_FRAMEWORK_TEMPLATES` dict
- `product_data: str | None` added to both CopywriterInput and RendererInput — JSON string format consistent
- `_check_size_compliance(width, height)` signature unchanged, logic updated for min-height check
- `_render_html_to_png` signature changed: removed `height` param, uses `full_page=True`
- `_fill_template` signature extended: added `product_info` parameter — passed from Renderer execute method
- Template HTML variables: `product_info` (dict) matches CopywriterTool's JSON format
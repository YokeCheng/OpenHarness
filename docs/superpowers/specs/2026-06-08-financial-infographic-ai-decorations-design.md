# 财经热点长图AI装饰元素生成设计文档

> 基于 OpenHarness 平台，在现有 financial-hotspot-pipeline 基础上，实现 HTML 固定布局 + AI 动态装饰元素生成的完整方案。
> 通过 LLM 智能理解内容主题并动态生成视觉风格建议，避免硬编码主题识别。

**日期**: 2026-06-08
**基座**: OpenHarness v0.1.9 + financial-hotspot-pipeline v1.0
**核心理念**: 动态提示词驱动，LLM 决定视觉风格

---

## 1. 项目背景

现有 financial-hotspot-pipeline 已实现完整的财经热点生图流水线，但 InfographicRendererTool 的 AI 装饰功能仍处于占位符状态。用户需求是将纯文字内容转换为包含丰富视觉元素的支付宝长图，具体包括：

- S0 HEAD 区：AI 生成科技主题背景图（电路板/卫星/存储等）
- S3 BODY 区：各模块标题的 AI 生成主题背景装饰
- S3 内容区：AI 生成数据可视化图表和产品图标
- 全局：色彩协调，确保整体视觉一致性

关键约束：
- **尺寸匹配率 100%**：宽度必须 1080px（一票否决项）
- **数据不出境**：必须使用国产模型
- **动态主题识别**：避免硬编码，通过 LLM 智能理解内容主题

---

## 2. 设计原则

### 2.1 动态提示词驱动
- **不硬编码主题识别**：让 LLM 从文案内容中理解主题并输出视觉建议
- **用户可参与决策**：提供视觉方案确认步骤，支持自定义
- **自动构建提示词**：基于 LLM 建议动态生成精准的 AI 图像生成提示词

### 2.2 分层架构
```
三层架构：
1. 内容层 (FinancialCopywriterTool) - 生成文案 + 视觉建议
2. 视觉层 (InfographicRendererTool) - HTML模板 + AI装饰生成  
3. 编排层 (Pipeline Skill) - 端到端流程 + 用户交互
```

### 2.3 技术选型
- **文案生成**: glm-4 → qwen-max → deepseek-v3 fallback
- **图像生成**: wanx-v1 → qwen-vl-plus fallback（阿里云一体化）
- **密钥复用**: 复用现有的 DASHSCOPE_API_KEY 配置
- **布局引擎**: Playwright 无头浏览器（确保 1080px 精确）

---

## 3. 核心组件设计

### 3.1 扩展 FinancialCopywriterTool

#### 3.1.1 视觉建议输出
在现有文案生成基础上，扩展输出格式：

```python
# ToolResult.metadata 新增字段
{
    "article_markdown": "完整 markdown 文案",
    "visual_theme": {
        "primary_theme": "半导体芯片",           # LLM 识别的主要主题
        "color_palette": "金橙科技色",          # 建议的配色方案
        "background_elements": [               # 建议的背景装饰元素
            "集成电路板", 
            "CPU芯片", 
            "向上增长箭头"
        ],
        "chart_styles": [                     # 建议的数据可视化类型
            "配比趋势图", 
            "市场规模柱状图", 
            "价格预测折线图"
        ]
    }
}
```

#### 3.1.2 Prompt 模板增强
在 `_FRAMEWORK_TEMPLATES["xingfengxiang"]` 末尾添加视觉指导：

```
此外，请基于文章内容提供视觉风格建议：
- 主要主题关键词（如：芯片、航天、存储等）
- 推荐的配色方案（如：金橙色、蓝色科技、绿色生态等）  
- 建议的背景装饰元素（如：电路板、卫星、数据流等）
- 适合的数据可视化类型（如：柱状图、趋势图、配比图等）

将这些建议以JSON格式附加到文章末尾，标记为【视觉建议】。
```

### 3.2 增强 InfographicRendererTool

#### 3.2.1 视觉建议解析
新增 `_extract_visual_theme()` 函数：

```python
def _extract_visual_theme(article: str) -> dict:
    """从文章末尾提取LLM生成的视觉建议"""
    if "【视觉建议】" in article:
        # 提取并解析JSON格式的视觉建议
        visual_json = extract_json_after_marker(article, "【视觉建议】")
        return json.loads(visual_json)
    else:
        # 默认回退到通用科技主题
        return _DEFAULT_VISUAL_THEME
```

#### 3.2.2 动态提示词构建
新增 `_build_dynamic_image_prompt()` 函数：

```python
def _build_dynamic_image_prompt(
    content_theme: str, 
    visual_suggestions: dict,
    element_type: str
) -> str:
    """动态构建AI图像生成提示词"""
    if element_type == "s0_background":
        return (
            f"高清{visual_suggestions['color_palette']}财经信息长图头部背景，"
            f"主题：{content_theme}，包含元素：{', '.join(visual_suggestions['background_elements'])}，"
            "无文字，纯装饰性，适合1080px宽度展示"
        )
    elif element_type == "section_header":
        return (
            f"{content_theme}主题装饰图案，{visual_suggestions['color_palette']}配色，"
            f"简洁科技风格，包含{', '.join(visual_suggestions['background_elements'][:2])}元素，"
            "适合作为二级标题背景，横向重复图案"
        )
    # ... 其他元素类型
```

#### 3.2.3 AI 图像生成集成
集成现有的 ImageGenerationTool：

```python
from openharness.tools.image_generation_tool import ImageGenerationTool

async def _generate_ai_image(prompt: str, size: str, context: ToolExecutionContext):
    """调用ImageGenerationTool生成AI图像"""
    image_tool = ImageGenerationTool()
    result = await image_tool.execute(
        ImageGenerationInput(
            prompt=prompt,
            model="wanx-v1",  # 或自动选择
            size=size
        ),
        context
    )
    return result.output_path if not result.is_error else None
```

#### 3.2.4 HTML 模板增强
更新 `template.html` 支持动态背景：

```html
<!-- S0 HEAD 区 -->
<div class="header" 
     {% if decoration_header %}style="background-image: url('{{ decoration_header }}')"{% endif %}>
  <!-- ... -->
</div>

<!-- S3 模块标题区 -->
{% for section in sections %}
<div class="section-container">
  <div class="section-header" 
       {% if section.background %}style="background-image: url('{{ section.background }}')"{% endif %}>
    <h2>{{ section.title }}</h2>
  </div>
  <!-- ... -->
</div>
{% endfor %}
```

### 3.3 更新 Pipeline Skill

#### 3.3.1 视觉风格确认步骤
在 Skill 中添加可选的视觉确认步骤：

```markdown
## 步骤2.5：确认视觉风格（可选）

如果用户未指定视觉风格，向用户展示LLM建议的视觉方案：
- 主题：{{ visual_theme.primary_theme }}
- 配色：{{ visual_theme.color_palette }}  
- 背景元素：{{ visual_theme.background_elements | join(', ') }}
- 是否接受此方案？[是/否/自定义]

如果用户选择自定义，询问具体的视觉要求。
```

#### 3.3.2 错误处理与降级
- **AI 生成失败**: 使用默认 CSS 背景色替代，不影响主流程
- **模型不可用**: 自动 fallback 到备用模型
- **尺寸不合规**: 自动重试最多 3 次

---

## 4. 文件变更清单

```
src/openharness/tools/
  financial_copywriter.py        ← 扩展视觉建议输出
  infographic_renderer.py       ← 增强AI装饰生成 + 视觉建议解析
  image_generation_tool.py      ← 确保支持 wanx-v1 模型（可能需要微调）

src/openharness/templates/
  xingfengxiang/
    template.html               ← 支持动态背景图像
    styles.css                  ← 保持现有样式，添加必要的背景支持

src/openharness/skills/
  financial_hotspot_pipeline.md ← 添加视觉风格确认步骤

docs/superpowers/specs/
  2026-06-08-financial-infographic-ai-decorations-design.md ← 本设计文档
```

---

## 5. 数据流总览

```
用户输入: "热点生图: 60只芯片股历史新高"

↓

Step 1: FinancialHotSpotScannerTool
  → 抓取相关热点数据

↓

Step 2: FinancialCopywriterTool  
  → 生成文案 + 【视觉建议】JSON
  → 输出: visual_theme = {primary_theme: "半导体芯片", ...}

↓

Step 2.5: (可选) 用户确认视觉风格
  → 接受/拒绝/自定义视觉方案

↓

Step 3: InfographicRendererTool
  → 解析 visual_theme
  → 动态构建 AI 图像生成提示词
  → 调用 ImageGenerationTool 生成:
     - S0 背景图 (1080x600)
     - S3 各模块标题背景 (1080x80 each)
     - S3 数据图表 (根据内容动态尺寸)
  → 填充 HTML 模板
  → Playwright 渲染 1080px 宽 PNG

↓

Step 4: 保存结果
  → infographic.png (1080px 宽，动态高度)
  → pipeline_log.json (包含视觉主题信息)
```

---

## 6. 合规与安全

- **数据不出境**: 所有模型调用通过国产 Provider (glm-anthropic / dashscope)
- **尺寸合规**: 强制验证 1080px 宽度，不合规自动重试
- **内容安全**: AI 生成的图像经过合规检查（无敏感内容）
- **可溯源性**: pipeline_log.json 记录使用的视觉主题和生成参数

---

## 7. 设计决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 主题识别方式 | LLM 动态建议 | 避免硬编码，支持任意新主题 |
| 图像生成模型 | wanx-v1 → qwen-vl-plus | 阿里云一体化，复用现有配置 |
| 用户交互 | 可选视觉确认 | 平衡自动化和用户控制 |
| 降级策略 | CSS 默认背景 | 确保主流程不受 AI 失败影响 |
| 提示词构建 | 动态模板 | 精准匹配内容主题和视觉需求 |
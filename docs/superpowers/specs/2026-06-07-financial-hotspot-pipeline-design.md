# 财经热点生图流水线设计文档

> 基于 OpenHarness 平台，以 Skills + Tools 方式实现"热点抓取→文案生成→兴风向长图"全流程自动化。

**日期**: 2026-06-07
**方案**: 方案B — 纯 Skills 配置（不改核心代码，只新增 3 个 Tool + 1 个 Skill + cron 配置）
**基座**: OpenHarness v0.1.9

---

## 1. 项目背景

为兴业证券"互联网生态阵地 AI 热点生图测试服务"POC 项目提供技术方案。核心需求：

1. 实时财经热点数据接入与处理
2. AI 财经文案自动生成（符合金融合规标准）
3. AI"兴风向"信息长图生成（支付宝渠道专用，尺寸匹配率 100% 为一票否决项）
4. 全流程测试与支撑能力（进度同步、问题整改、数据留存）

### 关键约束

- 数据不出境：必须使用国产头部中文大模型（GLM-4 / Qwen-Max / DeepSeek-V3）
- 尺寸匹配率 100%：生图尺寸必须与支付宝兴风向要求完全匹配（一票否决）
- 事实性错误率 < 5%，合规违规率 < 1%
- 生成成功率 ≥ 98%
- 端到端耗时比纯人工缩短 50% 以上

---

## 2. 子项目拆分与依赖

```
子项目1: financial-hotspot-scanner（热点抓取 Tool）
  → 输入: topic 关键词（如"降息"、"创新药"）
  → 输出: 结构化热点数据 JSON + 格式化文本（按 topic 过滤）
  → 无外部依赖（独立可用）

子项目2: financial-copywriter（AI文案生成 Tool）
  → 输入: 子项目1 的 metadata.hotspots + framework（xingfengxiang/knowledge_popularization）+ product_data（可选）
  → 输出: 一篇聚焦文案 markdown + 合规检查结果
  → 依赖: 子项目1 + 国产大模型 Provider

子项目3: infographic-renderer（信息长图渲染 Tool）
  → 输入: 子项目2 的文案 markdown + product_data（可选）
  → 输出: 兴风向信息长图 PNG（1080px宽，高度动态伸缩≥1920px）
  → 依赖: 子项目2 + HTML模板 + 无头浏览器

子项目4: financial-hotspot-pipeline（编排 Skill + cron）
  → 编排: 0(确认主题)→1(搜索热点)→2(生成文案)→3(生成长图) 的串联执行
  → 支持三种内容类型: knowledge_popularization / xingfengxiang / xingfengxiang+产品
  → 触发: cron 定时（每天9:00）或手动 /financial_hotspot_pipeline
  → 依赖: 1, 2, 3 全部完成
```

迭代顺序：1 → 2 → 3 → 4（流水线顺序优先）

---

## 3. 新增文件清单

```
src/openharness/tools/
  financial_hotspot_scanner.py   ← 子项目1
  financial_copywriter.py        ← 子项目2
  infographic_renderer.py        ← 子项目3

src/openharness/skills/
  financial_hotspot_pipeline.md  ← 子项目4

src/openharness/templates/
  xingfengxiang/
    template.html                ← 兴风向长图 HTML 模板
    styles.css                   ← 模板样式
    assets/                      ← 图标、配色素材（SVG/PNG）

src/openharness/tools/__init__.py  ← 改动：注册 3 个新 Tool（唯一改动的已有文件）
```

**核心原则**：只新增文件，只改 `__init__.py` 注册部分，不改其他核心代码。

---

## 4. 子项目1：FinancialHotSpotScannerTool

### 4.1 用途

抓取财经热点，返回结构化数据（文本 + metadata JSON）。

### 4.2 Input 模型

```python
class FinancialHotSpotScannerInput(BaseModel):
    sources: list[str] = Field(
        default=["eastmoney", "sina_hot"],
        description="资讯源列表：eastmoney(东方财富), sina_hot(新浪热搜), weibo_hot(微博热搜)"
    )
    categories: list[str] = Field(
        default=["policy", "industry", "market", "company"],
        description="热点分类过滤：policy(政策), industry(行业), market(行情), company(公司)"
    )
    max_items: int = Field(
        default=10, ge=1, le=50,
        description="每个源最多抓取的热点数量"
    )
    topic: str | None = Field(
        default=None,
        description="定向搜索主题关键词；None则返回全量热点"
    )
```

### 4.3 Output 格式

ToolResult.output 为格式化文本：

```
财经热点扫描结果 (2026-06-07, 共 15 条)

[东方财富] 政策类:
1. 央行宣布降息0.25个百分点
   来源: 东方财富 | 时间: 2026-06-07 09:30 | 分类: policy
   摘要: 中国人民银行宣布下调MLF利率...
   链接: https://...

[微博热搜] 行业类:
2. #新能源汽车销量创新高#
   来源: 微博热搜 | 时间: 2026-06-07 10:15 | 分类: industry
   摘要: 5月新能源汽车销量突破...
   链接: https://...
```

ToolResult.metadata 供后续 Tool 程序化使用：

```python
{
    "hotspots": [
        {
            "title": "央行宣布降息0.25个百分点",
            "source": "eastmoney",
            "category": "policy",
            "summary": "...",
            "url": "https://...",
            "published_at": "2026-06-07T09:30:00",
        },
        ...
    ],
    "scan_time": "2026-06-07T17:00:00",
    "total_count": 15,
}
```

### 4.4 执行流程

1. 按 sources 列表，逐一调用对应抓取函数
2. 每个源用 httpx 抓取公开页面/API → 解析 → 去重 → 分类
3. 使用 `openharness.utils.network_guard.fetch_public_http_response()` 进行 HTTP 请求（遵循平台网络策略）
4. 合并所有源结果，按 categories 排序
5. 返回格式化文本 + metadata JSON

### 4.5 资讯源实现

- **eastmoney**: 东方财富热点 API 或热点页面 HTML 解析
- **sina_hot**: 新浪财经热搜榜单页面解析
- **weibo_hot**: 微博热搜榜单 API/页面解析（提取财经相关词条）

每个源一个独立的 `_fetch_<source>()` 私有函数，返回 `list[dict]`。

### 4.6 属性

- `is_read_only`: True
- `name`: "financial_hotspot_scanner"

---

## 5. 子项目2：FinancialCopywriterTool

### 5.1 用途

基于结构化热点数据，调用国产大模型生成符合金融合规标准的财经解读文案。

### 5.2 Input 模型

```python
class FinancialCopywriterInput(BaseModel):
    hotspot_data: str = Field(
        description="结构化热点数据（JSON格式），来自 FinancialHotSpotScannerTool 的 metadata.hotspots"
    )
    framework: str = Field(
        default="xingfengxiang",
        description="文案框架：xingfengxiang(兴风向解读), standard(标准分析), knowledge_popularization(知识普及)"
    )
    style: str = Field(
        default="professional_accessible",
        description="文案风格：professional_accessible(专业可读), academic(学术), popular(通俗)"
    )
    model: str | None = Field(
        default=None,
        description="指定大模型（如 glm-4, qwen-max, deepseek-v3）；None则自动选择"
    )
    product_data: str | None = Field(
        default=None,
        description="产品推荐数据（JSON格式），包含product_name, product_code, nav, recent_change, risk_level, recommendation。None则不插入产品推荐"
    )
```

### 5.3 Output 格式

ToolResult.output 为完整文案文本：

```
【兴风向·财经热点解读】央行降息0.25个百分点

一、事件概述
中国人民银行于2026年6月7日宣布...

二、政策解读
本次降息的背景是...

三、市场影响
对债券市场：...
对股市：...

四、投资建议
建议关注...

---
生成信息：模型=glm-4 | 框架=xingfengxiang | 字数=856 | 时间=2026-06-07T17:05:00
```

ToolResult.metadata：

```python
{
    "article_markdown": "完整 markdown 文案",
    "model_used": "glm-4",
    "framework": "xingfengxiang",
    "char_count": 856,
    "key_points": ["降息背景", "市场影响", "投资建议"],
    "compliance_check": {
        "passed": True,
        "issues": [],
        "sensitive_words_found": 0,
        "fact_check_confidence": 0.95,
    },
    "generated_at": "2026-06-07T17:05:00",
}
```

### 5.4 执行流程

1. 解析 hotspot_data JSON → 提取热点信息
2. 依据 framework 选择 prompt template：
   - `xingfengxiang`: 兴风向解读框架（事件概述→政策解读→市场影响→投资建议）
   - `standard`: 标准财经分析框架（背景→分析→前景）
   - `knowledge_popularization`: 知识普及框架（概念定义→核心要点→数据与趋势→投资参考）
3. 通过 OpenHarness 已有的 `AuthManager` + provider profile 获取国产模型 API key
4. 如果 product_data 有值，解析 JSON 并将产品推荐信息注入 user_prompt
5. 使用 `openharness.api.client` 发起大模型调用请求
5. 对输出做合规检查：
   - 敏感词过滤（预置金融合规敏感词库）
   - 事实性校验（与热点原始数据交叉比对）
   - 专业术语规范检查
6. 返回文案 + compliance_check 结果

### 5.5 合规检查机制

- **敏感词库**: 内置金融行业合规敏感词列表（政治敏感、违规宣传、虚假承诺等）
- **事实性校验**: 将文案中的关键数据/日期/数字与热点原始信息交叉比对
- **术语规范**: 检查专业术语是否使用标准表述（如"降息"而非"利息降了"）
- 合规未通过 → 在 metadata.compliance_check 中记录问题，但仍然返回文案供人工审核

### 5.6 属性

- `is_read_only`: True
- `name`: "financial_copywriter"

---

## 6. 子项目3：InfographicRendererTool

### 6.1 用途

将财经文案渲染为符合支付宝"兴风向"版式的信息长图 PNG。**尺寸匹配率 100% 是一票否决项**。

### 6.2 Input 模型

```python
class InfographicRendererInput(BaseModel):
    article_content: str = Field(
        description="财经文案内容（markdown格式），来自 FinancialCopywriterTool"
    )
    article_title: str = Field(
        description="文案标题"
    )
    template: str = Field(
        default="xingfengxiang_default",
        description="长图模板名：xingfengxiang_default(兴风向默认版式)"
    )
    output_dir: str | None = Field(
        default=None,
        description="输出目录；None则保存到项目数据目录"
    )
    ai_decorations: bool = Field(
        default=True,
        description="是否使用AI生成装饰元素（图标、插图等）"
    )
    product_data: str | None = Field(
        default=None,
        description="产品推荐数据（JSON格式），包含product_name等。None则不插入产品推荐卡"
    )
```

### 6.3 Output 格式

```
兴风向信息长图已生成

标题: 央行降息0.25个百分点
文件: /data/infographics/2026-06-07_xingfengxiang_policy.png
尺寸: 1080×3500px (宽度1080px标准，高度随内容伸缩)
模板: xingfengxiang_default
AI装饰: 已生成3个装饰元素

---
合规检查: 尺寸匹配 ✅ | 图文一致 ✅ | 内容安全 ✅
```

ToolResult.metadata：

```python
{
    "image_path": "/data/infographics/2026-06-07_xingfengxiang_policy.png",
    "width": 1080,
    "height": 3500,
    "size_compliance": True,
    "template_used": "xingfengxiang_default",
    "key_points_extracted": ["降息背景", "市场影响", "投资建议"],
    "ai_decorations": ["header_illustration", "chart_icon", "footer_badge"],
    "text_image_match_score": 0.98,
    "generated_at": "2026-06-07T17:10:00",
}
```

### 6.4 执行流程

1. **关键信息提取**: 从 article_content markdown 中自动提取核心观点、关键数据、重要结论
2. **加载 HTML 模板**: 读取 `xingfengxiang/template.html` + `styles.css`
3. **AI 装饰生成**（如果 ai_decorations=True）:
   - 调用国产图像模型生成装饰元素（标题插图、数据图表图标、底部徽章）
   - 通过 OpenHarness 已有的 `ImageGenerationTool` 或国产图像 API
4. **填充模板**: 将文案内容 + 装饰元素填充到 HTML 模板
5. **HTML → PNG 转换**: 使用 Playwright 无头浏览器将 HTML 截图为 PNG
   - 设定 viewport width=1080px, height 动态伸缩（使用 full_page=True 截图）
   - 这是保证宽度 100% 匹配的关键步骤
6. **尺寸合规检查**: 验证生成的 PNG 宽度=1080px、高度≥1920px（动态高度）
7. **图文一致性检查**: 验证长图中包含文案的所有关键要点
8. 返回图片路径 + 合规检查结果

### 6.5 混合方案实现细节

- **程序化排版（HTML+CSS）**: 保证版式精确、尺寸100%可控、图文要素匹配度高
- **AI装饰**: 国产图像模型生成视觉元素（图标、小插图、配色建议），提升美观度
- **合成流程**: AI装饰元素 → 嵌入HTML模板 → CSS精确定位 → 无头浏览器截图 → PNG

### 6.6 兴风向版式规范（模板设计）

- **标准尺寸**: 1080px宽度，高度动态伸缩（≥1920px）
- **版式结构**:
  - 顶部: 标题区（品牌标识 + 标题 + 日期）
  - 中部: 内容区（白色/淡金色交替背景，分段标题 + 正文 + 数据卡片）
  - 产品推荐区（可选）：产品推荐卡（金色边框，产品名称/代码/净值/涨跌/风险）
  - 底部: 结论区（金色背景，核心结论 + 风险提示 + 品牌落款）
- **配色**: 金橙暖色系（主色调：#EA580C/#FBB03B，背景：#FFF8E7/#FFFFFF交替）
- **左侧装饰条**: 12px金橙渐变装饰条贯穿全文
- **字体**: 系统字体 fallback（确保跨平台渲染一致）

### 6.7 属性

- `is_read_only`: False（写入图片文件到磁盘）
- `name`: "infographic_renderer"

---

## 7. 子项目4：financial-hotspot-pipeline Skill

### 7.1 用途

编排全流程：确认主题 → 搜索热点 → 文案生成 → 长图渲染 → 保存记录

支持三种内容类型：
- knowledge_popularization — 知识普及型（"什么是XX"）
- xingfengxiang — 纯热点分析型（"央行降息意味着什么"）
- xingfengxiang + 产品数据 — 热点+产品推荐型

### 7.2 Skill 文件

**位置**: `src/openharness/skills/bundled/content/financial_hotspot_pipeline.md`

**放置方式**: 作为 bundled skill，随平台发布，启动时自动加载。用户无需手动安装或配置。

**注册方式**: OpenHarness 的 SkillRegistry 在启动时扫描 `bundled/content/` 目录下的 `.md` 文件并自动注册。slash command `/financial-hotspot-pipeline` 在 Skill 被匹配时自动可用。用户输入包含"热点生图"等关键词时，Agent 通过 Skill 匹配自动加载。

### 7.3 Skill 内容

采用**指令式**步骤描述风格：每一步明确写 Tool 名称、参数、metadata 字段传递关系，Agent 按指令执行。

```markdown
---
name: financial-hotspot-pipeline
description: 给定主题→搜索热点→生成文案→渲染长图的全流程自动化
user-invocable: true
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
- **是否带产品推荐**：如果类型是热点+产品，需要提供产品数据（JSON格式）

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

### 7.4 触发机制

**窄触发策略**：只在以下明确场景触发，避免误触发：
- 斜杠命令 `/financial-hotspot-pipeline`
- 关键词"热点生图"、"财经热点生图"、"执行热点生图流程"
- 不会在普通的"财经"、"热点"、"文案"等单独关键词时触发

**Cron 配置**：说明文档式。Skill 内容中包含 CronCreate 配置指南，用户按需自行设置。不自动创建 cron job。

### 7.5 手动触发

在 OpenHarness 对话中输入：
```
/financial-hotspot-pipeline
```
或：
```
热点生图
```

### 7.6 设计决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| Skill 位置 | bundled/content/ | 随平台发布，自动加载，无需手动安装 |
| 步骤风格 | 指令式 | 结果可控、可复现，明确 Tool 名称和参数 |
| Pipeline 模式 | 主题驱动，一主题一图 | 聚焦单一话题，产出更精准 |
| 内容类型 | 三种: knowledge_popularization / xingfengxiang / xingfengxiang+产品 | 适配兴业证券不同业务场景 |
| 合规失败处理 | 保存 _nc.md，跳过渲染 | 简单可靠，问题留给人工审核 |
| LLM 失败处理 | 换模型重试一次再终止 | 增加成功概率，后备列表：glm-4→qwen-max→deepseek-v3 |
| 尺寸不合规重试 | 相同参数重试 3 次 | 简单直接，符合设计文档的一票否决要求 |
| 长图尺寸 | 1080px宽，高度动态伸缩(≥1920px) | 适应不同内容长度，避免固定高度截断 |
| 触发范围 | 窄触发（"热点生图"等特定词） | 避免误触发 |
| Cron 配置 | 说明文档式 | 用户按需设置，不自动创建 |

---

## 8. 数据流总览

```
Cron 定时 (每天9:00) / 手动 /financial_hotspot_pipeline
         ↓
Agent 读取 Skill: financial-hotspot-pipeline
         ↓
Step 0: 确认主题和内容类型 (topic, content_type, product_data)
         ↓
Step 1: FinancialHotSpotScannerTool
  输入: sources=["eastmoney","sina_hot","weibo_hot"], topic=用户主题, categories, max_items
  输出: 格式化文本 + metadata.hotspots (JSON，按topic过滤)
         ↓
Step 2: FinancialCopywriterTool
  输入: hotspots JSON + framework(根据content_type) + product_data(可选)
  输出: 一篇聚焦文案 markdown + compliance_check
  ↓ 不合规 → 保存 _nc.md，提示用户人工审核
  ↓ LLM失败 → 换模型重试一次 → 仍失败则终止Pipeline
         ↓
Step 3: InfographicRendererTool
  输入: article markdown + title + template + product_data(可选) + output_dir
  输出: PNG 图片 (1080px宽，高度动态) + size_compliance
  ↓ 尺寸不合规 → 相同参数重试（最多3次）→ 仍不合规标记 size_failed
         ↓
Step 4: 保存全流程结果
  hotspots.json | article.md | infographic.png | pipeline_log.json
```

---

## 9. 技术选型

| 项目 | 选型 | 理由 |
|------|------|------|
| 大模型（文案） | GLM-4 / Qwen-Max / DeepSeek-V3 | 国产头部中文模型，数据不出境 |
| 图像模型（装饰） | 通义万相 / 其他国产图像API | 国产模型，装饰元素生成 |
| HTML→PNG | Playwright 无头浏览器 | 精确尺寸控制，CSS完整渲染 |
| HTTP抓取 | httpx + network_guard | OpenHarness已有基础设施 |
| 数据存储 | 本地文件系统 | POC阶段无需数据库 |
| 定时触发 | OpenHarness CronScheduler | 平台内置，无需外部调度 |

---

## 10. 合规与安全

- **数据不出境**: 所有模型调用通过国产 Provider profile（glm-anthropic / moonshot / dashscope），API endpoint 在境内
- **内容安全审核**: FinancialCopywriterTool 内置合规检查（敏感词过滤 + 事实性校验）
- **尺寸合规**: InfographicRendererTool 强制验证尺寸，不合规自动重试
- **数据留存**: 全流程输入/中间产物/输出/修改记录全部保存到本地文件
- **可溯源性**: pipeline_log.json 记录每次运行的模型、耗时、合规结果
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
  → 输出: 结构化热点数据 JSON + 格式化文本
  → 无外部依赖（独立可用）

子项目2: financial-copywriter（AI文案生成 Tool）
  → 输入: 子项目1 的 metadata.hotspots
  → 输出: 财经解读文案 markdown + 合规检查结果
  → 依赖: 子项目1 + 国产大模型 Provider

子项目3: infographic-renderer（信息长图渲染 Tool）
  → 输入: 子项目2 的文案 markdown
  → 输出: 兴风向信息长图 PNG（1080×1920px）
  → 依赖: 子项目2 + HTML模板 + 无头浏览器

子项目4: financial-hotspot-pipeline（编排 Skill + cron）
  → 编排: 1→2→3 的串联执行
  → 触发: cron 定时（每天9:00）或手动 /financial-hotspot-pipeline
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
        description="文案框架：xingfengxiang(兴风向解读框架), standard(标准财经分析)"
    )
    style: str = Field(
        default="professional_accessible",
        description="文案风格：professional_accessible(专业可读), academic(学术), popular(通俗)"
    )
    model: str | None = Field(
        default=None,
        description="指定大模型（如 glm-4, qwen-max, deepseek-v3）；None则自动选择"
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
   - `standard`: 标准财经分析框架
3. 通过 OpenHarness 已有的 `AuthManager` + provider profile 获取国产模型 API key
4. 使用 `openharness.api.client` 发起大模型调用请求
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
```

### 6.3 Output 格式

```
兴风向信息长图已生成

标题: 央行降息0.25个百分点
文件: /data/infographics/2026-06-07_xingfengxiang_policy.png
尺寸: 1080×1920px (支付宝兴风向标准尺寸)
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
    "height": 1920,
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
   - 设定精确 viewport: 1080×1920px
   - 这是保证尺寸 100% 匹配的关键步骤
6. **尺寸合规检查**: 验证生成的 PNG 宽度=1080px、高度=1920px
7. **图文一致性检查**: 验证长图中包含文案的所有关键要点
8. 返回图片路径 + 合规检查结果

### 6.5 混合方案实现细节

- **程序化排版（HTML+CSS）**: 保证版式精确、尺寸100%可控、图文要素匹配度高
- **AI装饰**: 国产图像模型生成视觉元素（图标、小插图、配色建议），提升美观度
- **合成流程**: AI装饰元素 → 嵌入HTML模板 → CSS精确定位 → 无头浏览器截图 → PNG

### 6.6 兴风向版式规范（模板设计）

- **标准尺寸**: 1080px × 1920px（支付宝渠道要求）
- **版式结构**:
  - 顶部: 标题区（品牌标识 + 标题 + 日期）
  - 中部: 内容区（分段标题 + 正文 + 数据卡片）
  - 底部: 结论区（核心结论 + 风险提示 + 品牌落款）
- **配色**: 兴风向品牌色系（蓝色主色调 + 金色点缀）
- **字体**: 系统字体 fallback（确保跨平台渲染一致）

### 6.7 属性

- `is_read_only`: False（写入图片文件到磁盘）
- `name`: "infographic_renderer"

---

## 7. 子项目4：financial-hotspot-pipeline Skill

### 7.1 用途

编排全流程：热点抓取 → 文案生成 → 长图渲染 → 保存记录

### 7.2 Skill 文件

位置: `src/openharness/skills/financial_hotspot_pipeline.md`

```markdown
---
name: financial-hotspot-pipeline
description: 执行财经热点抓取→文案生成→兴风向长图的全流程
---

# 财经热点生图流程

当收到"执行热点生图"或"/financial-hotspot-pipeline"指令时，按以下步骤操作：

## 步骤1：抓取热点

调用 FinancialHotSpotScannerTool，参数：
- sources: ["eastmoney", "sina_hot", "weibo_hot"]
- categories: ["policy", "industry", "market", "company"]
- max_items: 10

保存步骤1的 ToolResult.metadata["hotspots"] 数据供后续步骤使用。
Agent 应将 metadata["hotspots"] 序列化为 JSON 字符串，作为步骤2的 hotspot_data 参数传入。

## 步骤2：生成文案

对每条热点，调用 FinancialCopywriterTool：
- hotspot_data: 将步骤1 ToolResult.metadata["hotspots"] 序列化为 JSON 字符串传入
- framework: "xingfengxiang"
- style: "professional_accessible"

检查 compliance_check：
- 如果 ToolResult.metadata["compliance_check"]["passed"] == False，记录问题并跳过该热点
- 如果 passed == True，继续步骤3

## 步骤3：生成长图

对每篇合规文案，调用 InfographicRendererTool：
- article_content: 从步骤2的 article_markdown
- article_title: 热点标题
- template: "xingfengxiang_default"
- ai_decorations: true

检查尺寸合规：
- 如果 ToolResult.metadata["size_compliance"] == False，必须重新渲染（最多重试3次）
- 如果重试3次仍不合规，标记为失败并记录原因

## 步骤4：保存与记录

将所有结果保存到 /data/financial_hotspot_pipeline/YYYY-MM-DD/ 目录：
- hotspots.json — 原始热点数据（步骤1完整输出）
- articles/YYYY-MM-DD_HH-MM_title.md — 每篇文案 markdown
- infographics/YYYY-MM-DD_HH-MM_title.png — 每张长图 PNG
- pipeline_log.json — 全流程日志

pipeline_log.json 格式：
{
    "run_time": "2026-06-07T09:00:00",
    "trigger": "cron" | "manual",
    "hotspots_scanned": 15,
    "articles_generated": 12,
    "articles_compliant": 10,
    "infographics_generated": 10,
    "infographics_size_compliant": 10,
    "failed_items": [],
    "total_duration_seconds": 180,
    "model_used": "glm-4"
}

## 注意事项

- 尺寸合规是强制要求（一票否决项），不合规的图片必须重新渲染
- 所有中间产物必须保存，不可丢弃
- 记录端到端耗时，用于效率对比
- 合规未通过的文案仍然保存（标记为 non_compliant），供人工审核
- 生成成功率需 ≥ 98%，失败的条目记录详细原因
```

### 7.3 Cron 配置

```bash
# 在 OpenHarness 对话中配置
cron: "0 9 * * *"  # 每天 9:00
prompt: "/financial-hotspot-pipeline"
```

或通过 CLI：
```bash
oh cron start
```

### 7.4 手动触发

在 OpenHarness 对话中输入：
```
/financial-hotspot-pipeline
```
或：
```
执行热点生图流程
```

### 7.5 Skill 注册方式

Skill 文件放置在 `src/openharness/skills/financial_hotspot_pipeline.md` 后，OpenHarness 的 SkillRegistry 在启动时自动扫描 skills 目录并注册。
slash command `/financial-hotspot-pipeline` 会在 Skill 被匹配时自动可用，无需额外注册步骤。
用户输入包含"热点生图"等关键词时，Agent 也会通过 Skill 匹匹配自动加载此 Skill。

---

## 8. 数据流总览

```
Cron 定时 (每天9:00) / 手动 /financial-hotspot-pipeline
         ↓
Agent 读取 Skill: financial-hotspot-pipeline
         ↓
Step 1: FinancialHotSpotScannerTool
  输入: sources=["eastmoney","sina_hot","weibo_hot"], categories, max_items
  输出: 格式化文本 + metadata.hotspots (JSON)
         ↓
Step 2: FinancialCopywriterTool (per hotspot)
  输入: metadata.hotspots + framework + style + model
  输出: 文案 markdown + compliance_check
  ↓ 不合规 → 跳过（标记 non_compliant，仍保存）
         ↓
Step 3: InfographicRendererTool (per compliant article)
  输入: article markdown + title + template + ai_decorations
  输出: PNG 图片 (1080×1920px) + size_compliance
  ↓ 尺寸不合规 → 重新渲染（最多3次）
         ↓
Step 4: 保存全流程结果
  hotspots.json | articles/*.md | infographics/*.png | pipeline_log.json
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
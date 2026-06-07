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
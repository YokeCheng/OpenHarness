---
name: financial-hotspot-pipeline
description: 执行财经热点抓取→文案生成→兴风向长图的全流程自动化
---

# 财经热点生图流程

当收到"热点生图"、"财经热点生图"、"/financial_hotspot_pipeline"指令时，按以下步骤操作：

## 步骤1：抓取热点

调用 FinancialHotSpotScannerTool，参数：
- sources: ["eastmoney", "sina_hot", "weibo_hot"]
- categories: ["policy", "industry", "market", "company"]
- max_items: 10

保存 ToolResult.metadata["hotspots"] 数据供后续步骤使用。

**错误处理**：
- 所有源抓取失败（ToolResult.is_error == True）→ Pipeline 终止，返回错误信息
- 部分源失败 → 继续执行，在最终 pipeline_log.json 中记录失败的源

## 步骤2：生成文案（按 category 分组）

将步骤1的 metadata["hotspots"] 按 category 字段分组：
- policy 类 → 一篇"政策解读"
- industry 类 → 一篇"行业分析"
- market 类 → 一篇"行情分析"
- company 类 → 一篇"公司动态"

对每个分组，调用 FinancialCopywriterTool：
- hotspot_data: 该分组 hotspots 的 JSON 序列化字符串。具体操作：从 metadata["hotspots"] 中筛选 category == 该分组名称的条目，用 json.dumps() 序列化为字符串传入
- framework: "xingfengxiang"
- style: "professional_accessible"
- model: null（自动选择）

**合规检查**：
- 如果 ToolResult.metadata["compliance_check"]["passed"] == False：
  → 保存文案为 non_compliant（文件名后缀 _nc.md），跳过步骤3渲染，Pipeline 继续
- 如果 passed == True：继续步骤3

**LLM 调用失败处理**：
- 调用失败时（ToolResult.is_error == True 且错误信息包含"大模型调用失败"或"API"）：
  → 按后备模型列表换模型重试一次：先尝试 qwen-max，再尝试 deepseek-v3
  → 重试时 FinancialCopywriterTool 参数改为 model: "qwen-max" 或 model: "deepseek-v3"
  → 仍失败 → 跳过该分组，记录失败原因和尝试过的模型列表，Pipeline 继续处理其他分组

## 步骤3：生成长图

对每篇合规通过的文案，调用 InfographicRendererTool：
- article_content: 来自步骤2 ToolResult.metadata["article_markdown"]
- article_title: 该分组的代表性热点标题（取该分组第一条热点的 title 字段）
- template: "xingfengxiang_default"
- ai_decorations: true
- output_dir: "{cwd}/data/financial_hotspot_pipeline/{YYYY-MM-DD}/infographics"

**尺寸合规检查**（一票否决项）：
- 如果 ToolResult.metadata["size_compliance"] == False：
  → 相同参数重新调用 InfographicRendererTool，最多重试 3 次
  → 3 次仍不合规 → 标记为 size_failed，记录原因，Pipeline 继续

## 步骤4：保存与记录

将所有结果保存到 {cwd}/data/financial_hotspot_pipeline/{YYYY-MM-DD}/ 目录：

1. hotspots.json — 用 file_write_tool 将步骤1完整的 metadata["hotspots"] JSON 写入
2. articles/ — 每篇文案用 file_write_tool 写入：
   - {category}.md — 合规文案的 metadata["article_markdown"]
   - {category}_nc.md — 非合规文案（标记 nc）
3. infographics/ — 已由步骤3的 InfographicRendererTool 自动写入
4. pipeline_log.json — 用 file_write_tool 写入全流程日志

pipeline_log.json 格式：
```json
{
    "run_time": "当前UTC时间ISO格式",
    "trigger": "manual",
    "hotspots_scanned": "步骤1的metadata.total_count",
    "articles_generated": "成功生成文案的分组数量",
    "articles_compliant": "compliance_check.passed == True 的分组数量",
    "non_compliant": ["合规失败的category列表"],
    "infographics_generated": "成功生成长图的数量",
    "infographics_size_compliant": "size_compliance == True 的数量",
    "size_failed": ["尺寸不合规的category列表"],
    "failed_items": [
        {"category": "失败分组名", "reason": "失败原因", "models_tried": ["尝试过的模型列表"]}
    ],
    "total_duration_seconds": "步骤1开始到步骤4结束的秒数",
    "model_used": "主要使用的模型名"
}
```

## 触发方式

- 斜杠命令：/financial_hotspot_pipeline
- 关键词："热点生图"、"财经热点生图"、"执行热点生图流程"

## Cron 定时配置（可选）

如需每天自动执行，可使用 CronCreate 工具配置：
- cron: "0 9 * * *"
- prompt: "/financial_hotspot_pipeline"
- durable: true

或通过命令行：oh cron start

## 注意事项

- 尺寸合规是强制要求（一票否决项），不合规的图片必须重新渲染
- 所有中间产物必须保存，不可丢弃（包括 non_compliant 文案）
- 记录端到端耗时，用于效率对比
- 合规未通过的文案仍然保存（标记 _nc），供人工审核
- 生成成功率需 ≥ 98%，失败的条目记录详细原因
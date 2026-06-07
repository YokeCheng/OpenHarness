"""Financial copywriter tool — AI-powered financial article generation with compliance checks."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from openharness.auth.storage import load_credential
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider configuration for domestic models
# ---------------------------------------------------------------------------

_PROVIDER_CONFIGS: dict[str, dict[str, str]] = {
    "glm-4": {
        "env_key": "ZHIPUAI_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "storage_provider": "zhipu",
    },
    "glm-4-flash": {
        "env_key": "ZHIPUAI_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "storage_provider": "zhipu",
    },
    "qwen-max": {
        "env_key": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "storage_provider": "dashscope",
    },
    "qwen-plus": {
        "env_key": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "storage_provider": "dashscope",
    },
    "deepseek-v3": {
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "storage_provider": "deepseek",
    },
    "deepseek-chat": {
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "storage_provider": "deepseek",
    },
    "moonshot-v1-8k": {
        "env_key": "MOONSHOT_API_KEY",
        "base_url": "https://api.moonshot.ai/v1",
        "storage_provider": "moonshot",
    },
}

_AUTO_SELECT_ORDER: list[str] = ["glm-4", "qwen-max", "deepseek-v3", "moonshot-v1-8k"]


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------

class FinancialCopywriterInput(BaseModel):
    """Arguments for the financial copywriter tool."""

    hotspot_data: str = Field(
        description="结构化热点数据（JSON格式），来自 FinancialHotSpotScannerTool 的 metadata.hotspots",
    )
    framework: str = Field(
        default="xingfengxiang",
        description="文案框架：xingfengxiang(兴风向解读框架), standard(标准财经分析)",
    )
    style: str = Field(
        default="professional_accessible",
        description="文案风格：professional_accessible(专业可读), academic(学术), popular(通俗)",
    )
    model: str | None = Field(
        default=None,
        description="指定大模型（如 glm-4, qwen-max, deepseek-v3）；None则自动选择",
    )


# ---------------------------------------------------------------------------
# Style instructions
# ---------------------------------------------------------------------------

_STYLE_INSTRUCTIONS: dict[str, str] = {
    "professional_accessible": (
        "请以专业但通俗易懂的语调撰写，确保普通投资者也能理解核心含义。"
        "使用规范的金融术语，但避免过度学术化表述。"
    ),
    "academic": (
        "请以严谨的学术风格撰写，引用相关政策条款和数据，逻辑严密。"
        "使用标准学术用语，适合机构研报风格。"
    ),
    "popular": (
        "请以轻松通俗的语调撰写，用比喻和生活化的语言解释金融概念。"
        "确保大众读者能快速理解，但不失准确性。"
    ),
}


# ---------------------------------------------------------------------------
# Prompt templates per framework
# ---------------------------------------------------------------------------

_FRAMEWORK_TEMPLATES: dict[str, str] = {
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
    ),
    "standard": (
        "你是一位专业的财经分析师，正在撰写标准财经分析文章。\n"
        "\n"
        "请按以下结构撰写文章：\n"
        "\n"
        "财经分析：{{标题}}\n"
        "\n"
        "## 背景\n"
        "描述事件背景和触发因素。\n"
        "\n"
        "## 分析\n"
        "深入分析事件对经济和各行业的影响。\n"
        "\n"
        "## 前景\n"
        "展望未来走势和可能的政策延续。\n"
        "\n"
        "合规要求：\n"
        "- 不得使用任何保证收益、稳赚不赔的表述\n"
        "- 不得给出具体买卖点位建议\n"
        "- 数据必须与原始信息一致\n"
    ),
}


# ---------------------------------------------------------------------------
# Compliance check: sensitive words
# ---------------------------------------------------------------------------

_SENSITIVE_WORDS: list[str] = [
    # Prohibited promise phrases (违规承诺)
    "稳赚不赔", "Guaranteed", "保证收益", "零风险", "必涨", "肯定涨",
    "绝对收益", "无风险收益", "保本保息",
    # Prohibited specific advice (违规具体建议)
    "建议买入", "买入点位", "卖出点位", "止损点位", "目标价位",
    # Political sensitivity (政治敏感)
    "政治动荡", "政权更迭",
    # Misleading exaggeration (夸大误导)
    "暴涨", "暴赚", "翻倍收益", "一夜暴富",
]


def _check_sensitive_words(article: str) -> dict[str, Any]:
    """Check article for financial compliance sensitive words."""
    issues: list[str] = []
    for word in _SENSITIVE_WORDS:
        if word in article:
            issues.append(f"发现敏感词: '{word}'")
    return {
        "sensitive_words_found": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Compliance check: fact verification against original hotspot data
# ---------------------------------------------------------------------------

_DIRECTION_TERMS: dict[str, str] = {
    "降息": "加息",
    "降准": "升准",
    "上涨": "下跌",
    "利好": "利空",
    "增长": "下降",
    "宽松": "紧缩",
    "扩大": "缩小",
    "提升": "降低",
    "增加": "减少",
}


def _check_facts(article: str, hotspots: list[dict[str, str]]) -> dict[str, Any]:
    """Cross-reference article claims against original hotspot data."""
    issues: list[str] = []
    matched_points: int = 0
    total_points: int = 0

    for hotspot in hotspots:
        title = hotspot.get("title", "")
        total_points += 1

        # Extract core topic from title (remove direction terms)
        core_topic = title
        for direction in _DIRECTION_TERMS:
            core_topic = core_topic.replace(direction, "")
        core_topic = core_topic.strip()

        # Match: check if original title or core topic appears in article
        if (title and title in article) or (core_topic and len(core_topic) > 1 and core_topic in article):
            matched_points += 1

        # Check for contradictory direction terms (always, regardless of match)
        for correct_term, wrong_term in _DIRECTION_TERMS.items():
            if correct_term in title and wrong_term in article:
                issues.append(
                    f"事实矛盾: 原始信息为'{correct_term}'，文案中出现'{wrong_term}'"
                )
            if wrong_term in title and correct_term in article:
                issues.append(
                    f"事实矛盾: 原始信息为'{wrong_term}'，文案中出现'{correct_term}'"
                )

    confidence = matched_points / max(total_points, 1)
    if issues:
        confidence *= 0.5

    return {
        "fact_check_confidence": round(confidence, 2),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Compliance check: terminology normalization
# ---------------------------------------------------------------------------

_INFORMAL_TO_STANDARD: dict[str, str] = {
    "利息降了": "降息",
    "利息涨了": "加息",
    "利息升了": "加息",
    "利息掉了": "降息",
    "股市崩了": "股市大跌",
    "股票涨疯了": "股市大涨",
    "放水": "宽松货币政策",
    "收水": "紧缩货币政策",
    "印钱": "货币扩张",
    "割韭菜": "投资者受损",
}


def _check_terminology(article: str) -> dict[str, Any]:
    """Check that professional terminology is used in standard form."""
    issues: list[str] = []
    for informal, standard in _INFORMAL_TO_STANDARD.items():
        if informal in article:
            issues.append(f"非规范术语: '{informal}'，建议使用标准表述'{standard}'")
    return {
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# LLM API call via OpenAI-compatible endpoint
# ---------------------------------------------------------------------------


def _resolve_model_config(model: str) -> tuple[str, str, str]:
    """Resolve a model name to (api_key, base_url, model_name)."""
    config = _PROVIDER_CONFIGS.get(model)
    if config is None:
        raise RuntimeError(f"未知的模型: {model}。支持的模型: {', '.join(_PROVIDER_CONFIGS.keys())}")

    api_key = os.environ.get(config["env_key"]) or load_credential(config["storage_provider"], "api_key")
    if not api_key:
        raise RuntimeError(
            f"模型 {model} 的 API key 未配置。请设置环境变量 {config['env_key']} "
            f"或通过 /config 工具配置 {config['storage_provider']} 的凭据。"
        )

    return api_key, config["base_url"], model


def _auto_select_model() -> tuple[str, str, str]:
    """Auto-select a model by trying each in _AUTO_SELECT_ORDER."""
    for model in _AUTO_SELECT_ORDER:
        try:
            api_key, base_url, model_name = _resolve_model_config(model)
            logger.info("Auto-selected model: %s", model_name)
            return api_key, base_url, model_name
        except RuntimeError:
            continue
    raise RuntimeError(
        f"无法自动选择模型：所有候选模型均未配置 API key。"
        f"请至少配置以下之一: {', '.join(_AUTO_SELECT_ORDER)}"
    )


async def _call_llm(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    base_url: str,
) -> str:
    """Call a domestic LLM via OpenAI-compatible API endpoint.

    When *api_key* or *base_url* is empty, the function will resolve the
    configuration from _PROVIDER_CONFIGS automatically.  This allows the
    caller to pass placeholder values when the model config is not yet
    resolved (e.g. during testing when this function is monkeypatched).
    """
    # Auto-select model when the given model name is the first candidate
    # and no explicit model was requested — try _AUTO_SELECT_ORDER.
    actual_model = model
    actual_key = api_key
    actual_url = base_url

    if not actual_key or not actual_url:
        # Try to resolve config for the specified model first
        try:
            resolved_key, resolved_url, resolved_model = _resolve_model_config(actual_model)
            actual_key = actual_key or resolved_key
            actual_url = actual_url or resolved_url
            actual_model = resolved_model
        except RuntimeError:
            # The specified model failed — try auto-select
            for candidate in _AUTO_SELECT_ORDER:
                try:
                    c_key, c_url, c_model = _resolve_model_config(candidate)
                    actual_key = c_key
                    actual_url = c_url
                    actual_model = c_model
                    logger.info("Auto-selected model: %s", actual_model)
                    break
                except RuntimeError:
                    continue
            if not actual_key or not actual_url:
                raise RuntimeError(
                    f"无法自动选择模型：所有候选模型均未配置 API key。"
                    f"请至少配置以下之一: {', '.join(_AUTO_SELECT_ORDER)}"
                )

    client = AsyncOpenAI(api_key=actual_key, base_url=actual_url)
    try:
        response = await client.chat.completions.create(
            model=actual_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2048,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("LLM返回空内容")
        return content.strip()
    except Exception as exc:
        raise RuntimeError(f"大模型调用失败: {exc}") from exc
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Key points extraction
# ---------------------------------------------------------------------------


def _extract_key_points(article: str) -> list[str]:
    """Extract key points from article by finding section headers or key phrases."""
    points: list[str] = []

    # Extract from markdown headers (## headings)
    header_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    for match in header_pattern.finditer(article):
        header = match.group(1).strip()
        # Remove numbering like "一、", "二、" etc.
        header = re.sub(r"^[一二三四五六七八九十]+、\s*", "", header)
        if header and len(header) > 2:
            points.append(header)

    # If fewer than 2 headers found, try extracting from "一、" style numbering
    if len(points) < 2:
        numbered_pattern = re.compile(r"^[一二三四五六七八九十]+、(.+)$", re.MULTILINE)
        for match in numbered_pattern.finditer(article):
            section = match.group(1).strip()
            if section and len(section) > 2:
                points.append(section)

    # Fallback: return first 3 non-empty lines as key points
    if not points:
        lines = [line.strip() for line in article.split("\n") if line.strip() and len(line.strip()) > 5]
        points = lines[:3]

    return points[:5]  # max 5 key points


# ---------------------------------------------------------------------------
# Main tool class
# ---------------------------------------------------------------------------

class FinancialCopywriterTool(BaseTool):
    """Generate financial copywriter articles with compliance checks using domestic LLMs."""

    name = "financial_copywriter"
    description = (
        "基于结构化热点数据，调用国产大模型生成符合金融合规标准的财经解读文案。"
        "支持兴风向(xingfengxiang)和标准(standard)两种文案框架，"
        "自动进行敏感词、事实性、术语合规检查。"
    )
    input_model = FinancialCopywriterInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: FinancialCopywriterInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context

        # 1. Parse hotspot_data JSON
        try:
            hotspots = json.loads(arguments.hotspot_data)
        except json.JSONDecodeError as exc:
            return ToolResult(
                output=f"hotspot_data JSON解析失败: {exc}",
                is_error=True,
            )

        if not isinstance(hotspots, list) or not hotspots:
            return ToolResult(
                output="热点数据为空或格式不正确：需要非空JSON数组",
                is_error=True,
            )

        # 2. Determine model name
        model_name = arguments.model or _AUTO_SELECT_ORDER[0]

        # 3. Build prompts from framework template + style
        framework = arguments.framework
        if framework not in _FRAMEWORK_TEMPLATES:
            return ToolResult(
                output=f"未知的文案框架: '{framework}'。支持: xingfengxiang, standard",
                is_error=True,
            )

        style = arguments.style
        if style not in _STYLE_INSTRUCTIONS:
            return ToolResult(
                output=f"未知的文案风格: '{style}'。支持: professional_accessible, academic, popular",
                is_error=True,
            )

        system_prompt = _FRAMEWORK_TEMPLATES[framework] + "\n\n" + _STYLE_INSTRUCTIONS[style]

        # Build user prompt from hotspot data
        hotspot_brief = "\n".join(
            f"- 标题: {h.get('title', '')} | 来源: {h.get('source', '')} | "
            f"分类: {h.get('category', '')} | 摘要: {h.get('summary', '')}"
            for h in hotspots
        )
        user_prompt = (
            f"请基于以下财经热点数据撰写解读文章：\n\n{hotspot_brief}\n\n"
            f"请确保文章内容与上述热点数据的事实一致，不得编造数据或歪曲事实。"
        )

        # 4. Call LLM (api_key/base_url resolved inside _call_llm when not provided)
        try:
            article = await _call_llm(
                model=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                api_key="",
                base_url="",
            )
        except RuntimeError as exc:
            return ToolResult(
                output=f"文案生成失败: {exc}",
                is_error=True,
            )

        # 5. Run compliance checks
        sensitive_result = _check_sensitive_words(article)
        fact_result = _check_facts(article, hotspots)
        terminology_result = _check_terminology(article)

        all_issues = (
            sensitive_result["issues"]
            + fact_result["issues"]
            + terminology_result["issues"]
        )
        compliance_passed = len(all_issues) == 0

        # 6. Extract key points from article
        key_points = _extract_key_points(article)

        # 7. Build output text
        generated_at = datetime.now(timezone.utc).isoformat()
        footer = (
            f"\n---\n"
            f"生成信息：模型={model_name} | 框架={framework} | "
            f"字数={len(article)} | 时间={generated_at[:19]}"
        )
        output_text = article + footer

        # 8. Build metadata
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
        }

        return ToolResult(output=output_text, metadata=metadata)
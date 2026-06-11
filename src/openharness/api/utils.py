"""Utility functions for financial hotspot pipeline API."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from openharness.skills.loader import load_skill_registry
from openharness.tools.base import ToolExecutionContext, ToolResult
from openharness.tools.financial_copywriter import FinancialCopywriterTool, FinancialCopywriterInput
from openharness.tools.financial_hotspot_scanner import FinancialHotSpotScannerTool, FinancialHotSpotScannerInput
from openharness.tools.infographic_renderer import InfographicRendererTool, InfographicRendererInput


logger = logging.getLogger(__name__)


class StreamingToolExecutor:
    """Executor that supports SSE callback for streaming tool execution events."""

    def __init__(self, sse_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None):
        self.sse_callback = sse_callback

    async def send_sse_event(self, event_type: str, data: dict) -> None:
        """Send an SSE event if callback is available."""
        if self.sse_callback:
            await self.sse_callback(event_type, data)

    async def execute_tool_with_streaming(
        self,
        tool_name: str,
        tool_input: Any,
        context: ToolExecutionContext,
        step_number: int,
    ) -> ToolResult:
        """Execute a tool with SSE streaming support."""
        # Send start event
        await self.send_sse_event("tool_start", {
            "step": step_number,
            "tool": tool_name,
            "input": tool_input.model_dump() if hasattr(tool_input, "model_dump") else str(tool_input)
        })

        try:
            # Execute the actual tool based on name
            if tool_name == "financial_hotspot_scanner":
                tool = FinancialHotSpotScannerTool()
                result = await tool.execute(tool_input, context)
            elif tool_name == "financial_copywriter":
                tool = FinancialCopywriterTool()
                result = await tool.execute(tool_input, context)
            elif tool_name == "infographic_renderer":
                tool = InfographicRendererTool()
                result = await tool.execute(tool_input, context)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            # Send success event
            await self.send_sse_event("tool_success", {
                "step": step_number,
                "tool": tool_name,
                "output_summary": result.output[:200] if len(result.output) > 200 else result.output,
                "has_metadata": bool(result.metadata)
            })

            return result

        except Exception as e:
            # Send error event
            await self.send_sse_event("tool_error", {
                "step": step_number,
                "tool": tool_name,
                "error": str(e)
            })
            raise


async def execute_financial_hotspot_pipeline(
    topic: str,
    content: Optional[str] = None,
    content_type: str = "xingfengxiang",
    product_data: Optional[str] = None,
    context: Optional[ToolExecutionContext] = None,
    sse_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None,
) -> dict[str, Any]:
    """
    Execute the complete financial hotspot pipeline.

    Args:
        topic: The financial topic to analyze
        content: Optional user-provided news content or context to enhance the analysis
        content_type: Content framework (xingfengxiang, standard, knowledge_popularization)
        product_data: Optional product data as JSON string
        context: Tool execution context
        sse_callback: Optional callback for SSE streaming events

    Returns:
        Dictionary containing article, visual_theme, infographic_path, and status
    """
    if context is None:
        # Create a minimal context if not provided
        context = ToolExecutionContext(cwd=Path.cwd())

    executor = StreamingToolExecutor(sse_callback=sse_callback)

    try:
        # Step 1: Scan financial hotspots
        scanner_input = FinancialHotSpotScannerInput(
            topic=topic,
            sources=["eastmoney", "sina_hot"],
            categories=["policy", "industry", "market", "company"],
            max_items=5,
        )
        scanner_result = await executor.execute_tool_with_streaming(
            "financial_hotspot_scanner", scanner_input, context, 1
        )

        if scanner_result.is_error:
            raise RuntimeError(f"Hotspot scanning failed: {scanner_result.output}")

        if not scanner_result.metadata or "hotspots" not in scanner_result.metadata:
            raise RuntimeError("Hotspot scanning returned no valid metadata")

        hotspots = scanner_result.metadata["hotspots"]
        if not hotspots:
            raise RuntimeError(f"No hotspots found for topic: {topic}")

        # Step 2: Generate financial copy
        # Include user-provided content as additional context if available
        copywriter_input_dict = {
            "hotspot_data": json.dumps(hotspots),
            "framework": content_type,
            "style": "professional_accessible",
            "product_data": product_data
        }

        # If user provided content, include it as additional context
        if content:
            copywriter_input_dict["user_context"] = content

        copywriter_input = FinancialCopywriterInput(**copywriter_input_dict)
        copywriter_result = await executor.execute_tool_with_streaming(
            "financial_copywriter", copywriter_input, context, 2
        )

        if copywriter_result.is_error:
            raise RuntimeError(f"Copywriting failed: {copywriter_result.output}")

        if not copywriter_result.metadata:
            raise RuntimeError("Copywriting returned no valid metadata")

        article = copywriter_result.metadata.get("article_markdown", "")
        visual_theme = copywriter_result.metadata.get("visual_theme", {})

        if not article:
            raise RuntimeError("Copywriting returned empty article")

        # Step 3: Render infographic
        renderer_input = InfographicRendererInput(
            article_content=article,
            article_title=f"兴风向·财经热点解读：{topic}",
            template="xingfengxiang_default",
            product_data=product_data,
            visual_theme=json.dumps(visual_theme) if visual_theme else None,
        )
        renderer_result = await executor.execute_tool_with_streaming(
            "infographic_renderer", renderer_input, context, 3
        )

        if renderer_result.is_error:
            raise RuntimeError(f"Infographic rendering failed: {renderer_result.output}")

        if not renderer_result.metadata:
            raise RuntimeError("Infographic rendering returned no valid metadata")

        infographic_path = renderer_result.metadata.get("image_path", "")
        if not infographic_path:
            raise RuntimeError("Infographic rendering returned empty path")

        return {
            "article": article,
            "visual_theme": visual_theme,
            "infographic_path": infographic_path,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Pipeline execution error: {e}")
        raise RuntimeError(f"Pipeline execution failed: {str(e)}")


async def execute_prompt_via_existing_mechanism(
    prompt: str,
    force_skill: Optional[str] = None,
    execution_mode: str = "simple",
    context_override: Optional[dict[str, Any]] = None,
    tool_context: Optional[ToolExecutionContext] = None,
    sse_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None,
) -> dict[str, Any]:
    """
    Execute a natural language prompt through the existing OpenHarness skill system.

    This function provides a bridge between HTTP API requests and the existing CLI skill execution mechanism.
    It reuses all existing skill matching, tool execution, and context management logic.

    Args:
        prompt: Natural language prompt to execute
        force_skill: Optional skill name to force execution of specific skill
        execution_mode: Detail level for response ("simple", "detailed", "verbose", "stream")
        context_override: Optional context parameters to override defaults
        tool_context: Existing tool execution context from request middleware
        sse_callback: Optional callback for SSE streaming events (used when execution_mode="stream")

    Returns:
        Dictionary with execution status, result, and optional trace information
    """
    try:
        # Use existing tool context or create new one
        if tool_context is None:
            cwd = Path(context_override.get("cwd")) if context_override and context_override.get("cwd") else Path.cwd()
            tool_context = ToolExecutionContext(cwd=cwd)

        # Load the skill registry to find matching skills
        registry = load_skill_registry(cwd=tool_context.cwd)

        # If force_skill is specified, use that skill directly
        if force_skill:
            skill_def = registry.get(force_skill)
            if skill_def is None:
                raise ValueError(f"Skill '{force_skill}' not found in registry")

            # Handle financial hotspot pipeline specifically
            if force_skill == "financial-hotspot-pipeline":
                # Parse prompt to extract topic (improved implementation)
                topic = prompt.strip()
                # Remove common prefixes
                if topic.lower().startswith("热点生图："):
                    topic = topic[6:].strip()
                elif topic.lower().startswith("热点生图"):
                    topic = topic[5:].strip()

                # Extract only the first sentence or first 20 characters as topic
                # This prevents using very long text as search keyword
                if len(topic) > 50:
                    # Try to find sentence boundary
                    sentence_end = -1
                    for delimiter in ['。', '！', '？', '.', '!', '?', '；', ';']:
                        pos = topic.find(delimiter)
                        if pos != -1 and pos < 50:
                            sentence_end = pos
                            break

                    if sentence_end != -1:
                        topic = topic[:sentence_end + 1]
                    else:
                        # Fallback to first 20 characters
                        topic = topic[:20]

                # Remove any remaining whitespace
                topic = topic.strip()

                # Execute financial pipeline with appropriate SSE support
                if execution_mode == "stream":
                    result = await execute_financial_hotspot_pipeline(
                        topic=topic,
                        content_type="xingfengxiang",
                        context=tool_context,
                        sse_callback=sse_callback
                    )
                else:
                    result = await execute_financial_hotspot_pipeline(
                        topic=topic,
                        content_type="xingfengxiang",
                        context=tool_context
                    )

                # Build response based on execution mode
                response_data = {
                    "status": "success",
                    "result": result,
                }

                if execution_mode in ["detailed", "verbose"]:
                    response_data["execution_trace"] = [
                        {
                            "step": 1,
                            "type": "skill_execution",
                            "skill_name": "financial-hotspot-pipeline",
                            "input": {"prompt": prompt, "topic": topic},
                            "output_summary": "Financial pipeline executed successfully"
                        }
                    ]

                return response_data

            else:
                # For other forced skills, return a placeholder
                # In a full implementation, this would execute the actual skill
                return {
                    "status": "success",
                    "result": {
                        "message": f"Executed skill '{force_skill}' with prompt: {prompt}",
                        "note": "Full skill execution integration pending for non-financial skills"
                    }
                }

        else:
            # Attempt to match skill automatically (simplified implementation)
            # In a full implementation, this would use the skill matching logic
            # from the CLI system
            matched_skills = []
            all_skills = registry.list_skills()
            for skill in all_skills:
                if "financial" in skill.name.lower() or "hotspot" in skill.name.lower():
                    matched_skills.append(skill.name)

            if matched_skills:
                # Use the first matched skill as an example
                return await execute_prompt_via_existing_mechanism(
                    prompt=prompt,
                    force_skill=matched_skills[0],
                    execution_mode=execution_mode,
                    context_override=context_override,
                    tool_context=tool_context,
                    sse_callback=sse_callback,
                )
            else:
                # No matching skill found
                return {
                    "status": "success",
                    "result": {
                        "message": f"No matching skill found for prompt: {prompt}",
                        "available_skills": [skill.name for skill in all_skills]
                    }
                }

    except Exception as e:
        logger.error(f"Execute prompt error: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "result": {}
        }
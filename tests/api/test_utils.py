"""Tests for API utility functions with SSE support."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openharness.tools.base import ToolExecutionContext, ToolResult
from openharness.tools.financial_copywriter import FinancialCopywriterTool
from openharness.tools.financial_hotspot_scanner import FinancialHotSpotScannerTool
from openharness.tools.infographic_renderer import InfographicRendererTool

from src.openharness.api.utils import (
    StreamingToolExecutor,
    execute_financial_hotspot_pipeline,
    execute_prompt_via_existing_mechanism,
)


@pytest.mark.asyncio
async def test_streaming_tool_executor_callback():
    """Test that StreamingToolExecutor properly calls SSE callback."""
    mock_callback = AsyncMock()
    executor = StreamingToolExecutor(sse_callback=mock_callback)

    # Test with a simple event
    await executor.send_sse_event("test_type", {"data": "test"})

    mock_callback.assert_called_once_with("test_type", {"data": "test"})


@pytest.mark.asyncio
async def test_execute_financial_hotspot_pipeline_success():
    """Test successful execution of financial hotspot pipeline."""
    with patch.object(FinancialHotSpotScannerTool, 'execute') as mock_scan, \
         patch.object(FinancialCopywriterTool, 'execute') as mock_write, \
         patch.object(InfographicRendererTool, 'execute') as mock_render:

        # Mock scanner result
        mock_scan.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"hotspots": [{"title": "Test hotspot", "summary": "Test summary"}]}
        )

        # Mock copywriter result
        mock_write.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={
                "article_markdown": "# Test Article\nContent here",
                "visual_theme": {"primary_color": "#FF0000"}
            }
        )

        # Mock renderer result
        mock_render.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"image_path": "/tmp/test.png"}
        )

        context = ToolExecutionContext(cwd=Path.cwd())
        result = await execute_financial_hotspot_pipeline(
            topic="Test Topic",
            content_type="xingfengxiang",
            context=context
        )

        assert result["status"] == "success"
        assert "article" in result
        assert "visual_theme" in result
        assert "infographic_path" in result


@pytest.mark.asyncio
async def test_execute_prompt_via_existing_mechanism_streaming():
    """Test execute_prompt_via_existing_mechanism with streaming mode."""
    mock_callback = AsyncMock()

    with patch.object(FinancialHotSpotScannerTool, 'execute') as mock_scan, \
         patch.object(FinancialCopywriterTool, 'execute') as mock_write, \
         patch.object(InfographicRendererTool, 'execute') as mock_render:

        # Mock tool results
        mock_scan.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"hotspots": [{"title": "Test hotspot", "summary": "Test summary"}]}
        )
        mock_write.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={
                "article_markdown": "# Test Article\nContent here",
                "visual_theme": {"primary_color": "#FF0000"}
            }
        )
        mock_render.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"image_path": "/tmp/test.png"}
        )

        context = ToolExecutionContext(cwd=Path.cwd())
        result = await execute_prompt_via_existing_mechanism(
            prompt="热点生图：Test Topic",
            force_skill="financial-hotspot-pipeline",
            execution_mode="stream",
            tool_context=context,
            sse_callback=mock_callback
        )

        assert result["status"] == "success"
        assert "result" in result

        # Verify that SSE callback was called multiple times
        assert mock_callback.call_count >= 3  # At least once per tool + completion


@pytest.mark.asyncio
async def test_execute_prompt_via_existing_mechanism_simple():
    """Test execute_prompt_via_existing_mechanism with simple mode."""
    with patch.object(FinancialHotSpotScannerTool, 'execute') as mock_scan, \
         patch.object(FinancialCopywriterTool, 'execute') as mock_write, \
         patch.object(InfographicRendererTool, 'execute') as mock_render:

        # Mock tool results
        mock_scan.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"hotspots": [{"title": "Test hotspot", "summary": "Test summary"}]}
        )
        mock_write.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={
                "article_markdown": "# Test Article\nContent here",
                "visual_theme": {"primary_color": "#FF0000"}
            }
        )
        mock_render.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"image_path": "/tmp/test.png"}
        )

        context = ToolExecutionContext(cwd=Path.cwd())
        result = await execute_prompt_via_existing_mechanism(
            prompt="热点生图：Test Topic",
            force_skill="financial-hotspot-pipeline",
            execution_mode="simple",
            tool_context=context
        )

        assert result["status"] == "success"
        assert "result" in result
        assert "execution_trace" not in result


@pytest.mark.asyncio
async def test_execute_prompt_via_existing_mechanism_detailed():
    """Test execute_prompt_via_existing_mechanism with detailed mode."""
    with patch.object(FinancialHotSpotScannerTool, 'execute') as mock_scan, \
         patch.object(FinancialCopywriterTool, 'execute') as mock_write, \
         patch.object(InfographicRendererTool, 'execute') as mock_render:

        # Mock tool results
        mock_scan.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"hotspots": [{"title": "Test hotspot", "summary": "Test summary"}]}
        )
        mock_write.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={
                "article_markdown": "# Test Article\nContent here",
                "visual_theme": {"primary_color": "#FF0000"}
            }
        )
        mock_render.return_value = ToolResult(
            output="Success",
            is_error=False,
            metadata={"image_path": "/tmp/test.png"}
        )

        context = ToolExecutionContext(cwd=Path.cwd())
        result = await execute_prompt_via_existing_mechanism(
            prompt="热点生图：Test Topic",
            force_skill="financial-hotspot-pipeline",
            execution_mode="detailed",
            tool_context=context
        )

        assert result["status"] == "success"
        assert "result" in result
        assert "execution_trace" in result
        assert len(result["execution_trace"]) > 0
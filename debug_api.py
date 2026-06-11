#!/usr/bin/env python3
"""
Debug script for OpenHarness API
This script can be run directly in PyCharm for debugging.
"""
import uvicorn
from src.openharness.api.main import app

if __name__ == "__main__":
    # Start the FastAPI server with debugging enabled
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to False for debugging
        log_level="info"
    )
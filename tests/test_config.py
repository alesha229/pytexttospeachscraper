"""Tests for configuration module."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import (
    FIREWORKS_API_KEY,
    WHISK_COOKIE,
    LLM_MODEL,
    OUTPUT_DIR,
    IMAGE_OUTPUT_DIR,
)


def test_config_loads():
    """Test that config module loads without errors."""
    assert LLM_MODEL == "accounts/fireworks/models/qwen3p6-plus"
    assert OUTPUT_DIR.exists()
    assert IMAGE_OUTPUT_DIR.exists()


def test_env_variables():
    """Test that environment variables are loaded."""
    # These will be empty if .env is not configured
    assert isinstance(FIREWORKS_API_KEY, str)
    assert isinstance(WHISK_COOKIE, str)

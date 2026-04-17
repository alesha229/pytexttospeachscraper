"""Centralized configuration for PyTTS Scraper."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
WHISK_COOKIE = os.environ.get("WHISK_COOKIE", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
UNSPLASH_API_KEY = os.environ.get("UNSPLASH_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
BING_API_KEY = os.environ.get("BING_API_KEY", "")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
INWORLD_UID = os.environ.get("INWORLD_UID", "")

# LLM Settings
LLM_MODEL = "accounts/fireworks/models/qwen3p6-plus"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 4096
DEFAULT_LANGUAGE = "ru"

# Image Generation
IMAGE_MODEL = "IMAGEN_3_5"
IMAGE_ASPECT_RATIO = "IMAGE_ASPECT_RATIO_LANDSCAPE"
IMAGE_SEED = 0
IMAGE_COUNT = 1

# TTS Settings
TTS_SAMPLE_RATE = 48000
TTS_MAX_CHARS = 1000

# Output directories
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
IMAGE_OUTPUT_DIR = BASE_DIR / "image-output"
VIDEO_OUTPUT_DIR = BASE_DIR / "video-output"
BATCH_OUTPUT_DIR = BASE_DIR / "output_batch"
SEARCH_RESULTS_DIR = BASE_DIR / "search_results"
THUMBNAIL_DIR = BASE_DIR / "thumbnails"

# Create directories
for dir_path in [OUTPUT_DIR, IMAGE_OUTPUT_DIR, VIDEO_OUTPUT_DIR, 
                 BATCH_OUTPUT_DIR, SEARCH_RESULTS_DIR, THUMBNAIL_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
WHISK_COOKIE = os.environ.get("WHISK_COOKIE", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
UNSPLASH_API_KEY = os.environ.get("UNSPLASH_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
BING_API_KEY = os.environ.get("BING_API_KEY", "")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
INWORLD_UID = os.environ.get("INWORLD_UID", "")

LLM_MODEL = os.environ.get("LLM_MODEL", "accounts/fireworks/models/qwen3p6-plus")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "en")

VISION_MODEL = os.environ.get("VISION_MODEL", "accounts/fireworks/models/qwen3p6-plus")
VALIDATOR_CONFIDENCE_THRESHOLD = float(os.environ.get("VALIDATOR_CONFIDENCE_THRESHOLD", "0.6"))
VALIDATOR_MAX_ATTEMPTS = int(os.environ.get("VALIDATOR_MAX_ATTEMPTS", "5"))

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "IMAGEN_3_5")
IMAGE_ASPECT_RATIO = os.environ.get("IMAGE_ASPECT_RATIO", "IMAGE_ASPECT_RATIO_LANDSCAPE")
IMAGE_SEED = int(os.environ.get("IMAGE_SEED", "0"))
IMAGE_COUNT = int(os.environ.get("IMAGE_COUNT", "1"))

TTS_SAMPLE_RATE = int(os.environ.get("TTS_SAMPLE_RATE", "48000"))
TTS_MAX_CHARS = int(os.environ.get("TTS_MAX_CHARS", "1000"))
TTS_DEFAULT_VOICE_ID = os.environ.get("TTS_DEFAULT_VOICE_ID", "Blake")
TTS_MODEL_ID = os.environ.get("TTS_MODEL_ID", "inworld-tts-1.5-max")

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
DATA_DIR = APP_DIR / "data"

OUTPUT_DIR = BASE_DIR / "output"
IMAGE_OUTPUT_DIR = BASE_DIR / "image-output"
VIDEO_OUTPUT_DIR = BASE_DIR / "video-output"
AE_OUTPUT_DIR = BASE_DIR / "ae_output"
THUMBNAIL_DIR = BASE_DIR / "thumbnails"
SEARCH_RESULTS_DIR = BASE_DIR / "search_results"

for _d in [OUTPUT_DIR, IMAGE_OUTPUT_DIR, VIDEO_OUTPUT_DIR,
           AE_OUTPUT_DIR, THUMBNAIL_DIR, SEARCH_RESULTS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

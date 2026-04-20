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
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
INWORLD_UID = os.environ.get("INWORLD_UID", "")

LLM_MODEL = os.environ.get("LLM_MODEL", "accounts/fireworks/models/qwen3p6-plus")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "en")
SCENARIO_CHUNK_DURATION = int(os.environ.get("SCENARIO_CHUNK_DURATION", "300"))

VISION_MODEL = os.environ.get("VISION_MODEL", "accounts/fireworks/models/qwen3p6-plus")
VALIDATOR_CONFIDENCE_THRESHOLD = float(os.environ.get("VALIDATOR_CONFIDENCE_THRESHOLD", "0.6"))
VALIDATOR_MAX_ATTEMPTS = int(os.environ.get("VALIDATOR_MAX_ATTEMPTS", "5"))
STYLE_CONFIDENCE_THRESHOLD = float(os.environ.get("STYLE_CONFIDENCE_THRESHOLD", "0.5"))
HORROR_STYLE_PROMPT = os.environ.get("HORROR_STYLE_PROMPT", "Raw, visceral, photorealistic found footage horror, meticulously composed in a dark, intense aesthetic dominated by vibrant red and black with heavy VHS tape distortion. low-resolution diagnostic data and red-tinted text. The top screen is glitching, The whole image is plagued by rolling analog scanlines, extreme digital and chrominance noise, a heavy color grade favoring deep reds and decaying earth tones, and compression artifacts, filmed with a poor-quality, hand-held camcorder. In the bottom-right corner,. A heavy, dark, grimy vignette borders the 8k-based scene, featuring volumetric fog and a dark found-footage atmosphere.")

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "IMAGEN_3_5")
IMAGE_ASPECT_RATIO = os.environ.get("IMAGE_ASPECT_RATIO", "IMAGE_ASPECT_RATIO_LANDSCAPE")
IMAGE_SEED = int(os.environ.get("IMAGE_SEED", "0"))
IMAGE_COUNT = int(os.environ.get("IMAGE_COUNT", "1"))

UPSCALER_MODEL = os.environ.get("UPSCALER_MODEL", "4x-ultrasharp")
UPSCALER_MODEL_PATH = os.environ.get("UPSCALER_MODEL_PATH", "")
UPSCALER_SCALE = float(os.environ.get("UPSCALER_SCALE", "2"))
UPSCALER_TILE = int(os.environ.get("UPSCALER_TILE", "512"))
UPSCALER_GPU_ID = int(os.environ.get("UPSCALER_GPU_ID", "0"))
UPSCALER_HALF = os.environ.get("UPSCALER_HALF", "true").lower() in ("true", "1", "yes")
UPSCALER_GFPGAN = os.environ.get("UPSCALER_GFPGAN", "")
UPSCALER_MODEL_DIR = os.environ.get("UPSCALER_MODEL_DIR", "")
UPSCALER_SD_CHECKPOINT = os.environ.get("UPSCALER_SD_CHECKPOINT", "")
UPSCALER_SD_PROMPT = os.environ.get("UPSCALER_SD_PROMPT", "highly detailed vibrant colors, 4k")
UPSCALER_SD_NEGATIVE = os.environ.get("UPSCALER_SD_NEGATIVE", "low quality, blurry, jpeg artifacts, noise, grain, oversharpened, artifacts, deformed")
UPSCALER_SD_STRENGTH = float(os.environ.get("UPSCALER_SD_STRENGTH", "0.13"))
UPSCALER_SD_STEPS = int(os.environ.get("UPSCALER_SD_STEPS", "8"))
UPSCALER_SD_GUIDANCE = float(os.environ.get("UPSCALER_SD_GUIDANCE", "2.0"))
UPSCALER_SD_SAMPLER = os.environ.get("UPSCALER_SD_SAMPLER", "DPM++ SDE Karras")
UPSCALER_SD_VAE = os.environ.get("UPSCALER_SD_VAE", "")

TTS_SAMPLE_RATE = int(os.environ.get("TTS_SAMPLE_RATE", "48000"))
TTS_MAX_CHARS = int(os.environ.get("TTS_MAX_CHARS", "1000"))
TTS_DEFAULT_VOICE_ID = os.environ.get("TTS_DEFAULT_VOICE_ID", "Simon")
TTS_MODEL_ID = os.environ.get("TTS_MODEL_ID", "inworld-tts-1.5-max")
TTS_COOKIE = os.environ.get("TTS_COOKIE", "")

AE_TEMPLATE = os.environ.get("AE_TEMPLATE", "news")

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

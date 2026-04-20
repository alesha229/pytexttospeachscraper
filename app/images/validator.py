import os
import json
import base64
import time
import tempfile
import requests
from typing import Optional, Dict, List
from pathlib import Path
from openai import OpenAI

from ..config import FIREWORKS_API_KEY, VISION_MODEL, VALIDATOR_CONFIDENCE_THRESHOLD, STYLE_CONFIDENCE_THRESHOLD
from ..prompts import VALIDATOR_PROMPT, STYLE_VALIDATOR_PROMPT


class ImageValidator:
    def __init__(self, api_key: str = None, vision_model: str = None,
                 confidence_threshold: float = None,
                 style_confidence_threshold: float = None):
        self.api_key = api_key or FIREWORKS_API_KEY
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY not set")
        self.vision_model = vision_model or VISION_MODEL
        self.confidence_threshold = confidence_threshold or VALIDATOR_CONFIDENCE_THRESHOLD
        self.style_confidence_threshold = style_confidence_threshold or STYLE_CONFIDENCE_THRESHOLD
        self.video_theme = ""
        self.client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self.api_key,
        )

    def _encode_image_url(self, image_url: str) -> dict:
        return {"type": "image_url", "image_url": {"url": image_url}}

    def _encode_image_file(self, image_path: str) -> dict:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        ext = Path(image_path).suffix.lstrip(".") or "jpg"
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
        mime = mime_map.get(ext.lower(), "jpeg")
        return {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}}

    def _download_temp(self, image_url: str) -> Optional[str]:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        for attempt, ua in enumerate(user_agents):
            try:
                headers = {
                    "User-Agent": ua,
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
                    "sec-fetch-dest": "image",
                    "sec-fetch-mode": "no-cors",
                    "sec-fetch-site": "cross-site",
                }
                resp = requests.get(image_url, headers=headers, timeout=20, stream=True)
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                ext = ".jpg"
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"
                tmp_path = os.path.join(tempfile.gettempdir(), f"validate_{int(time.time())}{ext}")
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return tmp_path
            except Exception as e:
                if attempt < len(user_agents) - 1:
                    time.sleep(1)
                    continue
                print(f"  Download for validation failed: {e}")
                return None

    def validate(self, image_url: str = None, image_path: str = None,
                query: str = "", video_theme: str = None) -> Dict:
        if not query:
            return {"match": False, "description": "", "confidence": 0.0, "reason": "Empty query",
                    "style_match": True, "style_confidence": 0.0, "style_reason": ""}

        theme = video_theme if video_theme is not None else self.video_theme

        image_content = None

        if image_url:
            is_data_url = image_url.startswith("data:")
            is_accessible = any(image_url.startswith(p) for p in ["http://", "https://"])
            if is_data_url:
                image_content = {"type": "image_url", "image_url": {"url": image_url}}
            elif is_accessible:
                image_content = self._try_validate_from_url(image_url, query, theme)
                if image_content is not None:
                    return image_content
                return {"match": False, "description": "", "confidence": 0.0,
                        "reason": "Could not process URL",
                        "style_match": True, "style_confidence": 0.0, "style_reason": ""}

        if image_path and os.path.exists(image_path):
            image_content = self._encode_image_file(image_path)

        if image_content is None:
            return {"match": False, "description": "", "confidence": 0.0, "reason": "No image",
                    "style_match": True, "style_confidence": 0.0, "style_reason": ""}

        return self._call_vlm(image_content, query, theme)

    def _try_validate_from_url(self, image_url: str, query: str,
                               video_theme: str = "") -> Optional[Dict]:
        image_content = self._encode_image_url(image_url)
        try:
            result = self._call_vlm(image_content, query, video_theme)
            if result.get("confidence", 0) > 0:
                return result
        except Exception:
            pass

        tmp_path = self._download_temp(image_url)
        if tmp_path:
            try:
                image_content = self._encode_image_file(tmp_path)
                return self._call_vlm(image_content, query, video_theme)
            except Exception as e:
                return {"match": False, "description": "", "confidence": 0.0,
                        "reason": str(e),
                        "style_match": True, "style_confidence": 0.0, "style_reason": ""}
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        return None

    def _call_vlm(self, image_content: dict, query: str,
                  video_theme: str = "") -> Dict:
        if video_theme:
            prompt = STYLE_VALIDATOR_PROMPT.format(query=query, video_theme=video_theme)
        else:
            prompt = VALIDATOR_PROMPT.format(query=query)
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}, image_content]}]

        try:
            response = self.client.chat.completions.create(
                model=self.vision_model, messages=messages,
                temperature=0.3, max_tokens=1024,
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            if "match" in result:
                result["match"] = bool(result["match"])
            if "confidence" not in result:
                result["confidence"] = 0.5
            if video_theme:
                if "style_match" in result:
                    result["style_match"] = bool(result["style_match"])
                else:
                    result["style_match"] = True
                if "style_confidence" not in result:
                    result["style_confidence"] = 0.5
            else:
                result["style_match"] = True
                result["style_confidence"] = 1.0
                result["style_reason"] = "Style not checked"
            return result
        except json.JSONDecodeError:
            text_lower = raw.lower()
            match = '"match": true' in text_lower or '"match":true' in text_lower
            style_match = '"style_match": true' in text_lower or '"style_match":true' in text_lower
            if not video_theme:
                style_match = True
            return {"match": match, "description": raw[:200], "confidence": 0.3,
                    "reason": "Could not parse VLM JSON",
                    "style_match": style_match, "style_confidence": 0.3,
                    "style_reason": "Could not parse style from VLM JSON"}
        except Exception as e:
            return {"match": False, "description": "", "confidence": 0.0, "reason": str(e),
                    "style_match": True, "style_confidence": 0.0, "style_reason": str(e)}

    def is_valid(self, image_url: str = None, image_path: str = None,
                 query: str = "", video_theme: str = None) -> bool:
        result = self.validate(image_url=image_url, image_path=image_path,
                               query=query, video_theme=video_theme)
        return result["match"] and result["confidence"] >= self.confidence_threshold

    def is_style_match(self, image_url: str = None, image_path: str = None,
                       query: str = "", video_theme: str = None) -> bool:
        result = self.validate(image_url=image_url, image_path=image_path,
                               query=query, video_theme=video_theme)
        return result.get("style_match", True) and result.get("style_confidence", 0) >= self.style_confidence_threshold

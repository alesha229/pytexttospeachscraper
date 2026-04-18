import os
import json
import base64
import time
import tempfile
import requests
from typing import Optional, Dict, List
from pathlib import Path
from openai import OpenAI

from ..config import FIREWORKS_API_KEY, VISION_MODEL, VALIDATOR_CONFIDENCE_THRESHOLD
from ..prompts import VALIDATOR_PROMPT


class ImageValidator:
    def __init__(self, api_key: str = None, vision_model: str = None,
                 confidence_threshold: float = None):
        self.api_key = api_key or FIREWORKS_API_KEY
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY not set")
        self.vision_model = vision_model or VISION_MODEL
        self.confidence_threshold = confidence_threshold or VALIDATOR_CONFIDENCE_THRESHOLD
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
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
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
            print(f"  Download for validation failed: {e}")
            return None

    def validate(self, image_url: str = None, image_path: str = None, query: str = "") -> Dict:
        if not query:
            return {"match": False, "description": "", "confidence": 0.0, "reason": "Empty query"}

        image_content = None

        if image_url:
            is_data_url = image_url.startswith("data:")
            is_accessible = any(image_url.startswith(p) for p in ["http://", "https://"])
            if is_data_url:
                image_content = {"type": "image_url", "image_url": {"url": image_url}}
            elif is_accessible:
                image_content = self._try_validate_from_url(image_url, query)
                if image_content is not None:
                    return image_content
                return {"match": False, "description": "", "confidence": 0.0, "reason": "Could not process URL"}

        if image_path and os.path.exists(image_path):
            image_content = self._encode_image_file(image_path)

        if image_content is None:
            return {"match": False, "description": "", "confidence": 0.0, "reason": "No image"}

        return self._call_vlm(image_content, query)

    def _try_validate_from_url(self, image_url: str, query: str) -> Optional[Dict]:
        image_content = self._encode_image_url(image_url)
        try:
            result = self._call_vlm(image_content, query)
            if result.get("confidence", 0) > 0:
                return result
        except Exception:
            pass

        tmp_path = self._download_temp(image_url)
        if tmp_path:
            try:
                image_content = self._encode_image_file(tmp_path)
                return self._call_vlm(image_content, query)
            except Exception as e:
                return {"match": False, "description": "", "confidence": 0.0, "reason": str(e)}
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        return None

    def _call_vlm(self, image_content: dict, query: str) -> Dict:
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
            return result
        except json.JSONDecodeError:
            text_lower = raw.lower()
            match = '"match": true' in text_lower or '"match":true' in text_lower
            return {"match": match, "description": raw[:200], "confidence": 0.3, "reason": "Could not parse VLM JSON"}
        except Exception as e:
            return {"match": False, "description": "", "confidence": 0.0, "reason": str(e)}

    def is_valid(self, image_url: str = None, image_path: str = None, query: str = "") -> bool:
        result = self.validate(image_url=image_url, image_path=image_path, query=query)
        return result["match"] and result["confidence"] >= self.confidence_threshold

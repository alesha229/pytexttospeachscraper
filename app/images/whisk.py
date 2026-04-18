import base64
import time
from pathlib import Path

import requests


ASPECT_RATIOS = {
    "square": "IMAGE_ASPECT_RATIO_SQUARE",
    "portrait": "IMAGE_ASPECT_RATIO_PORTRAIT",
    "landscape": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    "1:1": "IMAGE_ASPECT_RATIO_SQUARE",
    "9:16": "IMAGE_ASPECT_RATIO_PORTRAIT",
    "16:9": "IMAGE_ASPECT_RATIO_LANDSCAPE",
}

MODELS = {
    "imagen3": "IMAGEN_3",
    "imagen3.5": "IMAGEN_3_5",
    "imagen4": "IMAGEN_4",
    "3": "IMAGEN_3",
    "3.5": "IMAGEN_3_5",
    "4": "IMAGEN_4",
}


class WhiskAPI:
    AUTH_URL = "https://labs.google/fx/api/auth/session"
    TRPC_URL = "https://labs.google/fx/api/trpc"
    MEDIA_URL = "https://aisandbox-pa.googleapis.com/v1"
    MEDIA_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY"

    def __init__(self, cookie: str):
        self.cookie = cookie
        self.auth_token = None
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self.session.cookies.set("__Secure-1PSID", cookie)

    def refresh_auth(self):
        try:
            response = self.session.get(
                self.AUTH_URL,
                headers={"cookie": f"__Secure-1PSID={self.cookie}"}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("error") == "ACCESS_TOKEN_REFRESH_NEEDED":
                raise Exception("Cookie expired - need new session")
            self.auth_token = data.get("access_token")
            if not self.auth_token:
                raise Exception(f"No access_token received. Response: {data}")
            return self.auth_token
        except Exception as e:
            raise Exception(f"Auth failed: {e}")

    def _post(self, url: str, body: dict, use_auth_token: bool = False) -> dict:
        headers = {}
        if use_auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        else:
            headers["cookie"] = f"__Secure-1PSID={self.cookie}"
        response = self.session.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response.json()

    def create_project(self, name: str = "Console Generator") -> str:
        body = {
            "json": {
                "workflowMetadata": {
                    "workflowName": name
                }
            }
        }
        response = self._post(
            f"{self.TRPC_URL}/media.createOrUpdateWorkflow",
            body
        )
        return response["workflowId"]

    def generate_image(
        self,
        prompt: str,
        model: str = "IMAGEN_3_5",
        aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
        seed: int = 0,
        count: int = 1,
    ) -> list:
        valid_models = ["IMAGEN_3", "IMAGEN_3_5", "IMAGEN_4"]
        if model not in valid_models:
            print(f"Invalid model {model}, using IMAGEN_3_5")
            model = "IMAGEN_3_5"

        valid_ratios = ["IMAGE_ASPECT_RATIO_SQUARE", "IMAGE_ASPECT_RATIO_PORTRAIT", "IMAGE_ASPECT_RATIO_LANDSCAPE"]
        if aspect_ratio not in valid_ratios:
            print(f"Invalid aspect_ratio {aspect_ratio}, using IMAGE_ASPECT_RATIO_LANDSCAPE")
            aspect_ratio = "IMAGE_ASPECT_RATIO_LANDSCAPE"

        body = {
            "userInput": {
                "candidatesCount": count,
                "prompts": [prompt],
                "seed": seed
            },
            "clientContext": {
                "sessionId": f";{int(time.time() * 1000)}",
                "tool": "IMAGE_FX"
            },
            "modelInput": {
                "modelNameType": model
            },
            "aspectRatio": aspect_ratio
        }

        try:
            response = self._post(
                f"{self.MEDIA_URL}:runImageFx",
                body,
                use_auth_token=True
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"API error (400): {e.response.text}")
                print(f"  Prompt: {prompt}")
                print(f"  Model: {model}")
                print(f"  Aspect: {aspect_ratio}")
            raise

        images = []
        for panel in response.get("imagePanels", []):
            for img in panel.get("generatedImages", []):
                returned_ratio = img.get("aspectRatio", "")
                if returned_ratio and returned_ratio != aspect_ratio:
                    print(f"  Warning: requested={aspect_ratio}, got={returned_ratio}")
                images.append({
                    "seed": img.get("seed"),
                    "prompt": img.get("prompt"),
                    "workflowId": img.get("workflowId"),
                    "encoded_media": img.get("encodedImage"),
                    "media_generation_id": img.get("mediaGenerationId"),
                    "aspect_ratio": img.get("aspectRatio"),
                    "model": img.get("modelNameType"),
                })
        return images

    def download_image_from_base64(self, base64_data: str, save_path: str) -> str:
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        image_bytes = base64.b64decode(base64_data)
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        return save_path

    def download_image_from_media_id(self, media_id: str, save_path: str) -> str:
        response = self.session.get(
            f"{self.MEDIA_URL}/media/{media_id}?key={self.MEDIA_KEY}",
            headers={
                "Referer": "https://labs.google/",
                "Authorization": f"Bearer {self.auth_token}",
            }
        )
        response.raise_for_status()
        data = response.json()
        media_info = data.get("image") or data.get("video")
        if not media_info:
            raise Exception("Could not get image data from API response")
        encoded_media = media_info.get("encodedImage") or media_info.get("encodedVideo")
        if not encoded_media:
            raise Exception("Encoded image missing in API response")
        return self.download_image_from_base64(encoded_media, save_path)


class ImageGenerator:
    def __init__(self, cookie: str, output_dir: str = "./output"):
        self.api = WhiskAPI(cookie)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        prompt: str,
        model: str = "IMAGEN_3_5",
        aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
        seed: int = 0,
        count: int = 1,
    ) -> list:
        print(f"Generating images...")
        print(f"  Prompt: {prompt}")
        print(f"  Model: {model}")
        print(f"  Aspect: {aspect_ratio}")

        print(f"Auth...")
        self.api.refresh_auth()
        print(f"  Success!")

        print(f"Generating...")
        images = self.api.generate_image(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            seed=seed,
            count=count,
        )

        if not images:
            print(f"Error: no images generated")
            return []

        saved_paths = []
        for i, img in enumerate(images, 1):
            timestamp = int(time.time())
            filename = f"generated_{timestamp}_{img['seed']}_{i}.png"
            filepath = self.output_dir / filename

            print(f"Saving image {i}/{len(images)}...")
            self.api.download_image_from_base64(img["encoded_media"], filepath)

            if aspect_ratio != "IMAGE_ASPECT_RATIO_LANDSCAPE":
                filepath = self._crop_to_aspect(filepath, aspect_ratio)

            saved_paths.append(str(filepath))
            print(f"  {filepath}")

        return saved_paths

    def _crop_to_aspect(self, filepath: Path, target_ratio: str) -> Path:
        from PIL import Image as PILImage

        ratio_map = {
            "IMAGE_ASPECT_RATIO_SQUARE": 1.0,
            "IMAGE_ASPECT_RATIO_PORTRAIT": 9 / 16,
            "IMAGE_ASPECT_RATIO_LANDSCAPE": 16 / 9,
        }
        target = ratio_map.get(target_ratio)
        if not target:
            return filepath

        img = PILImage.open(filepath)
        w, h = img.size
        current = w / h

        if abs(current - target) < 0.01:
            return filepath

        if current > target:
            new_w = int(h * target)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        img.save(filepath)
        print(f"  Cropped to {target_ratio}: {img.size[0]}x{img.size[1]}")
        return filepath

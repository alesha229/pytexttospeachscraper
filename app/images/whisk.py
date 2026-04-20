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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://labs.google",
            "Referer": "https://labs.google/",
        })
        
        if "__Secure-1PSID" in cookie:
            psid = cookie.split("__Secure-1PSID=")[1].split(";")[0]
            self.session.cookies.set("__Secure-1PSID", psid)
        
        if "__Secure-next-auth.session-token" in cookie:
            token = cookie.split("__Secure-next-auth.session-token=")[1].split(";")[0]
            self.session.cookies.set("__Secure-next-auth.session-token", token)
        
        if "__Host-next-auth.csrf-token" in cookie:
            csrf = cookie.split("__Host-next-auth.csrf-token=")[1].split(";")[0]
            self.session.cookies.set("__Host-next-auth.csrf-token", csrf)
        
        for cookie_part in cookie.split(";"):
            cookie_part = cookie_part.strip()
            if "=" in cookie_part:
                key, value = cookie_part.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key not in self.session.cookies:
                    self.session.cookies.set(key, value)

    def refresh_auth(self):
        try:
            response = self.session.get(
                self.AUTH_URL,
                headers={"cookie": self.cookie}
            )
            response.raise_for_status()
            data = response.json()
            print(f"  Auth response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
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
        response = self.session.post(url, json=body, headers=headers, timeout=180)
        response.raise_for_status()
        data = response.json()
        if "/trpc/" in url:
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                if isinstance(item, dict) and "result" in item:
                    result = item["result"]
                    if isinstance(result, dict) and "data" in result:
                        inner = result["data"]
                        if isinstance(inner, dict) and "json" in inner:
                            json_data = inner["json"]
                            if isinstance(json_data, dict) and "result" in json_data:
                                return json_data["result"]
                            return json_data
                        return inner
                    return result
                return item
            if isinstance(data, dict) and "result" in data:
                result = data["result"]
                if isinstance(result, dict) and "data" in result:
                    inner = result["data"]
                    if isinstance(inner, dict) and "json" in inner:
                        json_data = inner["json"]
                        if isinstance(json_data, dict) and "result" in json_data:
                            return json_data["result"]
                        return json_data
                    return inner
                return result
        return data

    def _to_data_url(self, image_base64: str, mime: str = "image/jpeg") -> str:
        if image_base64.startswith("data:"):
            return image_base64
        return f"data:{mime};base64,{image_base64}"

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

    def caption_image(self, image_base64: str, count: int = 1) -> list:
        body = {
            "json": {
                "captionInput": {
                    "candidatesCount": count,
                    "mediaInput": {
                        "rawBytes": self._to_data_url(image_base64),
                        "mediaCategory": "MEDIA_CATEGORY_SUBJECT"
                    }
                }
            }
        }
        response = self._post(
            f"{self.TRPC_URL}/backbone.captionImage",
            body
        )
        captions = []
        for candidate in response.get("candidates", []):
            captions.append(candidate.get("output", ""))
        return captions

    def upload_image(self, image_base64: str, caption: str,
                     category: str = "MEDIA_CATEGORY_BOARD",
                     workflow_id: str = "") -> str:
        body = {
            "json": {
                "clientContext": {
                    "workflowId": workflow_id
                },
                "uploadMediaInput": {
                    "mediaCategory": category,
                    "rawBytes": self._to_data_url(image_base64),
                    "caption": caption
                }
            }
        }
        response = self._post(
            f"{self.TRPC_URL}/backbone.uploadImage",
            body
        )
        return response.get("uploadMediaGenerationId", "")

    def refine_image(self, image_base64: str, caption: str,
                     edit_instruction: str, aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
                     workflow_id: str = "", media_generation_id: str = "") -> list:
        edit_input = {
            "caption": caption,
            "userInstruction": edit_instruction,
            "mediaInput": {
                "mediaCategory": "MEDIA_CATEGORY_BOARD",
                "rawBytes": self._to_data_url(image_base64)
            },
            "seed": None,
            "safetyMode": None,
        }
        if media_generation_id:
            edit_input["originalMediaGenerationId"] = media_generation_id

        body = {
            "json": {
                "clientContext": {
                    "workflowId": workflow_id
                },
                "imageModelSettings": {
                    "aspectRatio": aspect_ratio,
                    "imageModel": "GEM_PIX",
                },
                "editInput": edit_input
            },
            "meta": {
                "values": {
                    "editInput.seed": ["undefined"],
                    "editInput.safetyMode": ["undefined"]
                }
            }
        }

        try:
            print(f"  Sending refine request to Whisk API...")
            response = self._post(
                f"{self.TRPC_URL}/backbone.editImage",
                body
            )
            print(f"  Refine response received, processing...")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"Refine API error (400): {e.response.text}")
                print(f"  Caption: {caption}")
                print(f"  Edit: {edit_instruction}")
            raise
        except requests.exceptions.Timeout:
            print(f"  Refine request timeout after 180 seconds")
            raise Exception("Whisk refine API timeout")
        except requests.exceptions.ConnectionError as e:
            print(f"  Refine connection error: {e}")
            raise Exception("Whisk refine API connection error")

        images = []
        for panel in response.get("imagePanels", []):
            for img in panel.get("generatedImages", []):
                images.append({
                    "seed": img.get("seed"),
                    "prompt": img.get("prompt"),
                    "workflowId": img.get("workflowId"),
                    "encoded_media": img.get("encodedImage"),
                    "media_generation_id": img.get("mediaGenerationId"),
                    "aspect_ratio": img.get("aspectRatio"),
                    "model": img.get("imageModel", "GEM_PIX"),
                    "refined": True,
                })
        return images

    def _run_image_recipe(self, user_instruction: str, recipe_inputs: list,
                          aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
                          workflow_id: str = "") -> list:
        body = {
            "clientContext": {
                "workflowId": workflow_id,
                "tool": "BACKBONE",
            },
            "seed": 0,
            "imageModelSettings": {
                "imageModel": "GEM_PIX",
                "aspectRatio": aspect_ratio,
            },
            "userInstruction": user_instruction,
            "recipeMediaInputs": recipe_inputs,
        }

        try:
            print(f"  Sending recipe request...")
            response = self._post(
                f"{self.MEDIA_URL}/whisk:runImageRecipe",
                body,
                use_auth_token=True
            )
            print(f"  Recipe response received")
        except requests.exceptions.HTTPError as e:
            print(f"  Recipe error ({e.response.status_code}): {e.response.text[:200]}")
            raise
        except Exception as e:
            print(f"  Recipe request error: {e}")
            raise

        images = []
        for panel in response.get("imagePanels", []):
            for img in panel.get("generatedImages", []):
                images.append({
                    "seed": img.get("seed"),
                    "prompt": img.get("prompt"),
                    "workflowId": img.get("workflowId", workflow_id),
                    "encoded_media": img.get("encodedImage"),
                    "media_generation_id": img.get("mediaGenerationId"),
                    "aspect_ratio": img.get("aspectRatio", aspect_ratio),
                    "model": img.get("imageModel", "GEM_PIX"),
                    "refined": True,
                })
        return images

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
            print(f"  Sending request to Whisk API...")
            response = self._post(
                f"{self.MEDIA_URL}:runImageFx",
                body,
                use_auth_token=True
            )
            print(f"  Response received, processing...")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"API error (400): {e.response.text}")
                print(f"  Prompt: {prompt}")
                print(f"  Model: {model}")
                print(f"  Aspect: {aspect_ratio}")
            raise
        except requests.exceptions.Timeout:
            print(f"  Request timeout after 180 seconds")
            raise Exception(f"Whisk API timeout - image generation took too long")
        except requests.exceptions.ConnectionError as e:
            print(f"  Connection error: {e}")
            raise Exception(f"Whisk API connection error")

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

    def refine(self, image_path: str, edit_instruction: str,
               caption: str = "", aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE") -> list:
        print(f"Refining image via Whisk...")
        print(f"  Source: {image_path}")
        print(f"  Edit: {edit_instruction[:80]}")

        ext = Path(image_path).suffix.lstrip(".").lower()
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}
        img_type = mime_map.get(ext, "jpeg")

        with open(image_path, "rb") as f:
            image_base64 = f"data:image/{img_type};base64,{base64.b64encode(f.read()).decode('utf-8')}"

        print(f"Auth...")
        self.api.refresh_auth()
        print(f"  Success!")

        if not caption:
            print(f"  Generating caption...")
            try:
                captions = self.api.caption_image(image_base64, count=1)
                caption = captions[0] if captions else "An image"
                print(f"  Caption: {caption[:80]}")
            except Exception as e:
                print(f"  Caption failed: {e}")
                caption = "An image"

        print(f"  Creating project...")
        workflow_id = ""
        try:
            workflow_id = self.api.create_project("Style Transfer")
            print(f"  Project: {workflow_id}")
        except Exception as e:
            print(f"  Project creation failed: {e}")

        style_media_id = ""
        if workflow_id:
            print(f"  Uploading image as style reference...")
            try:
                style_media_id = self.api.upload_image(
                    image_base64, caption, "MEDIA_CATEGORY_STYLE", workflow_id
                )
                print(f"  Style ref ID: {style_media_id}")
            except Exception as e:
                print(f"  Style upload failed: {e}")

        images = None

        if workflow_id and style_media_id:
            print(f"  Generating with style reference (runImageRecipe)...")
            try:
                recipe_inputs = [
                    {
                        "caption": caption,
                        "mediaInput": {
                            "mediaCategory": "MEDIA_CATEGORY_STYLE",
                            "mediaGenerationId": style_media_id,
                        }
                    }
                ]
                images = self.api._run_image_recipe(
                    user_instruction=edit_instruction,
                    recipe_inputs=recipe_inputs,
                    aspect_ratio=aspect_ratio,
                    workflow_id=workflow_id,
                )
            except Exception as e:
                print(f"  Recipe with style ref failed: {e}")
                images = None

        if images is None and workflow_id:
            print(f"  Fallback: generating with rawBytes style reference...")
            try:
                recipe_inputs = [
                    {
                        "caption": caption,
                        "mediaInput": {
                            "mediaCategory": "MEDIA_CATEGORY_STYLE",
                            "rawBytes": image_base64,
                        }
                    }
                ]
                images = self.api._run_image_recipe(
                    user_instruction=edit_instruction,
                    recipe_inputs=recipe_inputs,
                    aspect_ratio=aspect_ratio,
                    workflow_id=workflow_id,
                )
            except Exception as e:
                print(f"  RawBytes recipe failed: {e}")
                return []

        if not images:
            print(f"Error: no refined images returned")
            return []

        saved_paths = []
        for i, img_data in enumerate(images, 1):
            timestamp = int(time.time())
            filename = f"refined_{timestamp}_{img_data.get('seed', 0)}_{i}.png"
            filepath = self.output_dir / filename

            print(f"Saving refined image {i}/{len(images)}...")
            self.api.download_image_from_base64(img_data["encoded_media"], filepath)

            if aspect_ratio != "IMAGE_ASPECT_RATIO_LANDSCAPE":
                filepath = self._crop_to_aspect(filepath, aspect_ratio)

            saved_paths.append(str(filepath))
            print(f"  {filepath}")

        return saved_paths

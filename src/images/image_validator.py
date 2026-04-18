"""
Модуль валидации изображений с помощью Qwen VL (Vision-Language) через Fireworks AI.
Отправляет найденное фото в VLM и спрашивает: соответствует ли изображение поисковому запросу?
Если нет - возвращает False, и поиск продолжается.

Использование:
    validator = ImageValidator()
    result = validator.validate(image_url="https://...", query="Илон Маск")
    # result = {"match": True, "description": "На фото мужчина в костюме...", "confidence": 0.9}
    
    # Интегрированный поиск с валидацией:
    result = validator.search_and_validate(query="Илон Маск", max_attempts=5)

Вход:
    - image_url (str) или image_path (str): URL или путь к изображению
    - query (str): Поисковый запрос (что мы искали)

Выход:
    - dict: {"match": bool, "description": str, "confidence": float}
"""

import os
import json
import base64
import time
import tempfile
import requests
from typing import Optional, Dict, List
from pathlib import Path
from openai import OpenAI
from ddgs import DDGS

from src.config import FIREWORKS_API_KEY, SEARCH_RESULTS_DIR


CONFIG = {
    "api_key": os.environ.get("FIREWORKS_API_KEY", ""),
    "vision_model": "accounts/fireworks/models/qwen3p6-plus",
    "temperature": 0.3,
    "max_tokens": 1024,
    "confidence_threshold": 0.6,
    "max_validate_attempts": 5,
    "temp_dir": None,
}

VALIDATION_PROMPT = """Ты — эксперт по валидации изображений. Тебе нужно определить, соответствует ли изображение поисковому запросу.

Поисковый запрос: "{query}"

Проанализируй изображение и ответь в СТРОГО следующем JSON формате (без markdown, без лишнего текста):
{{
  "match": true/false,
  "description": "Краткое описание того, что изображено на фото",
  "confidence": 0.0-1.0,
  "reason": "Почему изображение соответствует или не соответствует запросу"
}}

Критерии оценки:
- match=true если на изображении ЧЕТКО видно то, что запрашивалось
- match=false если изображение НЕ связано с запросом, слишком абстрактное, или на нём совсем другое
- match=false если на изображении есть ВОТЕРМАРКА — любой полупрозрачный текст/логотип поверх фото (shutterstock, getty, istock, depositphotos и т.д.), даже если она частичная или в углу
- confidence от 0.0 до 1.0 — насколько ты уверен
- Если на фото рекламный баннер, иконка, логотип или интерфейс вместо реального фото — ставь match=false
- Если фото размытое, обрезанное или плохого качества — снижай confidence
- Особое внимание: ватермарки стоковых сайтов (shutterstock, getty images, istock, adobe stock, alamy, 123rf, depositphotos, dreamstime, bigstock и др.) — ВСЕГДА ставь match=false

Отвечай ТОЛЬКО валидным JSON, без markdown блоков, без пояснений."""


class ImageValidator:
    def __init__(
        self,
        api_key: str = None,
        vision_model: str = None,
        confidence_threshold: float = None,
        temp_dir: str = None,
    ):
        self.api_key = api_key or CONFIG["api_key"] or FIREWORKS_API_KEY
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY не указан")

        self.vision_model = vision_model or CONFIG["vision_model"]
        self.confidence_threshold = confidence_threshold or CONFIG["confidence_threshold"]
        self.temp_dir = temp_dir or CONFIG["temp_dir"]

        self.client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self.api_key,
        )

    def _encode_image_url(self, image_url: str) -> dict:
        return {
            "type": "image_url",
            "image_url": {
                "url": image_url,
            },
        }

    def _encode_image_file(self, image_path: str) -> dict:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        ext = Path(image_path).suffix.lstrip(".") or "jpg"
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
        mime = mime_map.get(ext.lower(), "jpeg")
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/{mime};base64,{b64}",
            },
        }

    def _download_temp(self, image_url: str) -> Optional[str]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            resp = requests.get(image_url, headers=headers, timeout=20, stream=True)
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")
            ext = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"

            tmp_dir = self.temp_dir or tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, f"validate_{int(time.time())}{ext}")
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return tmp_path
        except Exception as e:
            print(f"   ⚠ Ошибка скачивания для валидации: {e}")
            return None

    def validate(
        self,
        image_url: str = None,
        image_path: str = None,
        query: str = "",
    ) -> Dict:
        """
        Валидирует изображение: соответствует ли оно поисковому запросу.

        Returns:
            {"match": bool, "description": str, "confidence": float, "reason": str}
        """
        if not query:
            return {"match": False, "description": "", "confidence": 0.0, "reason": "Пустой запрос"}

        print(f"      🔎 ВАЛИДАЦИЯ: запрос='{query}'")
        if image_url:
            print(f"         URL: {image_url[:80]}")
        if image_path:
            print(f"         Файл: {image_path}")

        image_content = None

        if image_url:
            is_data_url = image_url.startswith("data:")
            is_accessible = any(
                image_url.startswith(prefix)
                for prefix in ["http://", "https://"]
            )

            if is_data_url:
                image_content = {"type": "image_url", "image_url": {"url": image_url}}
            elif is_accessible:
                image_content = self._try_validate_from_url(image_url, query)
                if image_content is not None:
                    return image_content
                return {"match": False, "description": "", "confidence": 0.0, "reason": "Не удалось обработать URL"}

        if image_path and os.path.exists(image_path):
            image_content = self._encode_image_file(image_path)

        if image_content is None:
            return {"match": False, "description": "", "confidence": 0.0, "reason": "Нет изображения"}

        return self._call_vlm(image_content, query)

    def _try_validate_from_url(self, image_url: str, query: str) -> Optional[Dict]:
        """Пробуем сначала отправить URL напрямую, если не выходит — скачиваем и шлём файл."""
        print(f"         📤 Отправка URL в Qwen VL напрямую...")
        image_content = self._encode_image_url(image_url)
        try:
            result = self._call_vlm(image_content, query)
            if result.get("confidence", 0) > 0:
                return result
        except Exception as e:
            print(f"         ⚠ Прямая отправка не удалась: {e}")

        print(f"         📥 Скачивание изображения для валидации...")
        tmp_path = self._download_temp(image_url)
        if tmp_path:
            try:
                image_content = self._encode_image_file(tmp_path)
                result = self._call_vlm(image_content, query)
                return result
            except Exception as e:
                print(f"   ⚠ Ошибка валидации через файл: {e}")
                return {"match": False, "description": "", "confidence": 0.0, "reason": str(e)}
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        return None

    def _call_vlm(self, image_content: dict, query: str) -> Dict:
        """Вызов VLM модели через Fireworks API."""
        prompt = VALIDATION_PROMPT.format(query=query)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    image_content,
                ],
            }
        ]

        try:
            print(f"         🤖 Qwen VL: запрос к модели {self.vision_model}...")
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=messages,
                temperature=CONFIG["temperature"],
                max_tokens=CONFIG["max_tokens"],
            )

            raw = response.choices[0].message.content.strip()

            raw = raw.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw)

            if "match" in result:
                result["match"] = bool(result["match"])
            if "confidence" not in result:
                result["confidence"] = 0.5

            match_str = "✅ ПОДХОДИТ" if result.get("match") else "❌ НЕ ПОДХОДИТ"
            print(f"         🤖 Qwen VL ответ: {match_str}")
            print(f"            Описание: {result.get('description', '?')[:100]}")
            print(f"            Confidence: {result.get('confidence', 0)}")
            print(f"            Причина: {result.get('reason', '?')[:100]}")

            return result

        except json.JSONDecodeError:
            text_lower = raw.lower()
            match = '"match": true' in text_lower or '"match":true' in text_lower
            match_str = "✅ ПОДХОДИТ" if match else "❌ НЕ ПОДХОДИТ"
            print(f"         🤖 Qwen VL: не удалось распарсить JSON ({match_str})")
            print(f"            Сырой ответ: {raw[:150]}")
            return {
                "match": match,
                "description": raw[:200],
                "confidence": 0.3,
                "reason": "Не удалось распарсить JSON ответ VLM",
            }
        except Exception as e:
            print(f"         ⚠ Ошибка Qwen VL: {e}")
            return {"match": False, "description": "", "confidence": 0.0, "reason": str(e)}

    def is_valid(self, image_url: str = None, image_path: str = None, query: str = "") -> bool:
        """Быстрая проверка: подходит ли изображение (True/False)."""
        result = self.validate(image_url=image_url, image_path=image_path, query=query)
        return result["match"] and result["confidence"] >= self.confidence_threshold

    def search_and_validate(
        self,
        query: str,
        count: int = 1,
        max_attempts: int = None,
        orientation: str = "landscape",
        save_dir: str = None,
    ) -> List[Dict]:
        """
        Ищет изображения через DuckDuckGo и валидирует каждое через Qwen VL.
        Возвращает только подходящие изображения.

        Args:
            query: Поисковый запрос
            count: Сколько валидных изображений нужно найти
            max_attempts: Максимум попыток поиска (по умолчанию count * 3)
            orientation: Ориентация
            save_dir: Папка для сохранения валидных изображений

        Returns:
            Список валидных результатов с добавленным полем "validation"
        """
        max_attempts = max_attempts or CONFIG["max_validate_attempts"] * count
        validated_results = []
        all_seen_urls = set()
        consecutive_empty_batches = 0

        print(f"\n🔍 Поиск с валидацией: '{query}' (нужно {count}, макс попыток {max_attempts})")

        attempts = 0

        while len(validated_results) < count and attempts < max_attempts:
            remaining = count - len(validated_results)
            batch_size = min(remaining + 3, 10)
            attempts += batch_size

            try:
                with DDGS() as ddgs:
                    ddgs_results = list(ddgs.images(
                        query,
                        region='wt-wt',
                        safesearch='off',
                        max_results=batch_size,
                    ))
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "Ratelimit" in error_msg:
                    print(f"   ⏳ Rate limit DuckDuckGo, ждём...")
                    time.sleep(3)
                    continue
                print(f"   ⚠ Ошибка поиска: {e}")
                break

            if not ddgs_results:
                print(f"   ⚠ DuckDuckGo не вернул результатов")
                break

            new_urls = [img.get("image", "") for img in ddgs_results if img.get("image", "") and img.get("image", "") not in all_seen_urls]
            
            if not new_urls:
                consecutive_empty_batches += 1
                if consecutive_empty_batches >= 2:
                    print(f"   ⚠ Нет новых результатов, все уже проверены. Прерываем.")
                    break
                print(f"   ⚠ Все результаты уже проверены, пробуем ещё раз...")
                time.sleep(3)
                continue
            else:
                consecutive_empty_batches = 0

            for img in ddgs_results:
                if len(validated_results) >= count:
                    break

                image_url = img.get("image", "")
                if not image_url or image_url in all_seen_urls:
                    continue
                all_seen_urls.add(image_url)

                print(f"   🧪 Валидация: {image_url[:60]}...")

                validation = self.validate(image_url=image_url, query=query)

                is_match = validation["match"] and validation["confidence"] >= self.confidence_threshold

                status = "✅ ПОДХОДИТ" if is_match else "❌ НЕ подходит"
                print(f"   {status} (conf={validation.get('confidence', 0):.1f}): {validation.get('description', '')[:60]}")

                result = {
                    "id": str(hash(image_url)),
                    "source": "duckduckgo",
                    "source_type": "real",
                    "url": img.get("url", ""),
                    "photographer": img.get("source", "Unknown"),
                    "alt": img.get("title", ""),
                    "download_url": image_url,
                    "is_real": True,
                    "validation": validation,
                    "validated": is_match,
                }

                if is_match:
                    if save_dir:
                        os.makedirs(save_dir, exist_ok=True)
                        filename = f"validated_{query.replace(' ', '_')}_{len(validated_results)+1}.jpg"
                        save_path = os.path.join(save_dir, filename)
                        try:
                            self._download_image(image_url, save_path)
                            result["local_path"] = save_path
                            print(f"   💾 Сохранено: {filename}")
                        except Exception as e:
                            print(f"   ⚠ Ошибка сохранения: {e}")

                    validated_results.append(result)

                time.sleep(0.5)

            if len(validated_results) < count:
                print(f"   🔄 Найдено {len(validated_results)}/{count} валидных, ищем дальше...")
                time.sleep(2)

        print(f"\n{'✅' if validated_results else '❌'} Валидных изображений: {len(validated_results)}/{count}")

        return validated_results

    def _download_image(self, url: str, save_path: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return save_path

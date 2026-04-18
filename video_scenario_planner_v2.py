"""
Модуль генерации сценария видео V2 с использованием Fireworks AI
Преобразует входящую тему или текст в детализированный JSON-план для видеомонтажного движка.

Использование:
    python video_scenario_planner_v2.py "Тема видео"
    python video_scenario_planner_v2.py "Тема" --language en --duration 60
    python video_scenario_planner_v2.py --topic "Тема" --style cinematic --scenes 5

Вход:
    - topic (str): Тема видео (обязательно)
    - api-key (str): Fireworks API key (или через FIREWORKS_API_KEY)
    - language (str): Язык озвучки (по умолчанию "ru")
    - duration (int): Целевая длительность в секундах (по умолчанию 30)
    - style (str): Стиль видео (опционально)
    - scenes (int): Количество сцен (опционально)

Выход:
    - JSON файл сценария (по умолчанию scenario_{topic}.json)
    - Структура JSON:
        {
            "metadata": {
                "vibe": "Стиль видео",
                "tempo": "Темп",
                "assets": ["список ассетов"]
            },
            "timeline": [
                {
                    "voiceover": "Текст для озвучки",
                    "background": {
                        "type": "stock_video | generated_image | person_photo",
                        "prompt": "Промпт для фона"
                    },
                    "overlays": [
                        {
                            "type": "thesis | quote | nameplate",
                            "text": "Текст оверлея"
                        }
                    ]
                }
            ],
            "assets_manifest": [
                {
                    "type": "person | location | object",
                    "name": "Имя сущности",
                    "description": "Описание для поиска/генерации"
                }
            ]
        }
"""

import json
import os
import time
import wave
from pathlib import Path
from typing import Optional, Dict, List
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

from image_generator import ImageGenerator, WhiskAPI, CONFIG as IMAGE_CONFIG
from image_search import ImageSearch
from tts_engine import tts, COOKIES as TTS_COOKIES
from thumbnail_generator import ThumbnailGenerator

# ============================================================
# ⚙️ КОНФИГУРАЦИЯ
# ============================================================
CONFIG = {
    "api_key": os.environ.get("FIREWORKS_API_KEY", ""),
    "model": "accounts/fireworks/models/qwen3p6-plus",
    "temperature": 0.7,
    "max_tokens": 4096,
    "default_language": "ru",
}
# ============================================================


class FireworksClient:
    """Клиент для Fireworks AI API через OpenAI-совместимый интерфейс"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["api_key"] or os.environ.get("FIREWORKS_API_KEY")
        if not self.api_key:
            raise ValueError("API ключ не указан. Установите FIREWORKS_API_KEY или укажите в CONFIG")
        
        self.client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self.api_key,
        )
    
    def generate(self, messages: list, model: str = None, temperature: float = None, max_tokens: int = None) -> str:
        """
        Генерация ответа от LLM
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            model: Модель (если None, используется CONFIG)
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Текст ответа
        """
        # Fireworks AI требует stream=true для max_tokens > 4096
        use_stream = max_tokens is not None and max_tokens > 4000
        
        print(f"  🔌 Запрос к LLM: model={model or CONFIG['model']}, max_tokens={max_tokens or CONFIG['max_tokens']}, stream={use_stream}")
        
        try:
            response = self.client.chat.completions.create(
                model=model or CONFIG["model"],
                messages=messages,
                temperature=temperature if temperature is not None else CONFIG["temperature"],
                max_tokens=max_tokens or CONFIG["max_tokens"],
                stream=use_stream,
            )
            
            if use_stream:
                print("  📡 Получаем ответ через стриминг...")
                full_response = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                if not full_response:
                    raise ValueError("API вернул пустой стрим. Проверьте API ключ и модель.")
                print(f"  ✅ Получено {len(full_response)} символов")
                return full_response
            else:
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("API вернул пустое содержание. Проверьте API ключ.")
                print(f"  ✅ Получено {len(content)} символов")
                return content
        except Exception as e:
            print(f"❌ Ошибка запроса к LLM: {e}")
            raise


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "video_output_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class VideoScenarioPlannerV2:
    """
    Планировщик видео-сценария V2
    Создает детальный JSON-план для видеомонтажного движка с разделением на фон и оверлеи
    """
    
    SYSTEM_PROMPT = """You are a Technical Director and Screenwriter for an automated YouTube channel. Your task: transform an input topic or text into a detailed JSON plan for a video editing engine.

### YOUR THINKING LOGIC:
1. CONTENT ANALYSIS: Break the text into logical blocks. In each block, identify: the main idea, key persons, quotes, and emotional tone.
2. VISUALIZATION LAYERS: For each segment, determine what goes as background (Background) and what goes on top (Overlay).
3. REAL PERSONS: If a real person is mentioned, automatically create a 'person' object with their name for searching their photo online.
4. ON-SCREEN UNITS: Do not copy the voiceover text. Create short units for the screen:
   - thesis: A short thesis (2-5 words) displayed in the center of the screen
   - quote: A quote with the author's name (if there is a real source)
   - news_item: News/fact from the internet (requires web search)
   - person_photo: Person's photo (needs search_query for finding)
   - object_photo: Photo of an object/location (search_query for stock)

### JSON STRUCTURE REQUIREMENTS:
- 'metadata': Overall video style (vibe), tempo, and list of all needed assets for preloading.
- 'timeline': An array of objects (blocks), where each block contains:
    - 'voiceover': Text for voiceover narration.
    - 'background': Type (stock_video, generated_image, person_photo) and corresponding prompt/query.
    - 'overlays': List of ON-SCREEN UNITS (maximum 1-2 per scene):
        * thesis: {"type": "thesis", "content": "SHORT THESIS", "emphasis": "high"}
        * quote: {"type": "quote", "content": "Quote text", "source": "Author", "search_query": "query for verification"}
        * news_item: {"type": "news_item", "headline": "Headline", "source": "Website", "search_query": "query"}
        * person_photo: {"type": "person_photo", "name": "Name", "search_query": "query for finding photo"}
        * object_photo: {"type": "object_photo", "name": "Object", "search_query": "query for stock photo"}
- 'assets_manifest': List of SPECIFIC entities for generation/search. 
  IMPORTANT: Do not write categories. Write specific objects with search_query:
  [{"type": "person", "name": "Victor Surge", "search_query": "Victor Surge Eric Knudsen photo"}, {"type": "location", "name": "Forest", "search_query": "dark foggy forest night"}].

### TEXT STYLE:
Use vivid, modern language. Avoid bureaucratic phrasing. Text should sound like natural speech from a narrator.

### OUTPUT FORMAT:
Output ONLY pure JSON. No introductory words or explanations."""
    
    def __init__(
        self,
        api_key: str = None,
        fireworks_api_key: str = None,
        whisk_cookie: str = None,
        inworld_cookies: dict = None,
        pexels_api_key: str = None,
        use_real_photos: bool = True,
        use_stock_photos: bool = False
    ):
        self.client = FireworksClient(api_key or fireworks_api_key)
        self.whisk_cookie = whisk_cookie or IMAGE_CONFIG.get("cookie")
        self.inworld_cookies = inworld_cookies
        self.use_real_photos = use_real_photos
        self.use_stock_photos = use_stock_photos
        
        self.image_generator = None
        self.thumbnail_generator = None
        self.image_search = None
        self.has_image_search = False
        
        if self.whisk_cookie:
            self.image_generator = ImageGenerator(cookie=self.whisk_cookie, output_dir="")
            self.thumbnail_generator = ThumbnailGenerator(
                whisk_cookie=self.whisk_cookie,
                output_dir=os.path.join(OUTPUT_DIR, "thumbnails")
            )
        
        try:
            self.image_search = ImageSearch(
                pexels_key=pexels_api_key,
                use_duckduckgo=use_real_photos
            )
            self.has_image_search = True
        except ValueError:
            print("⚠ Не удалось инициализировать поиск изображений.")
    
    def create_scenario(
        self,
        topic: str,
        language: str = None,
        target_duration: int = 30,
        style: str = None,
        num_scenes: int = None,
    ) -> dict:
        """
        Создание сценария видео
        
        Args:
            topic: Тема/идея видео
            language: Язык озвучки (ru, en)
            target_duration: Целевая длительность в секундах
            style: Стиль видео (cinematic, cartoon, realistic, minimal и т.д.)
            num_scenes: Желаемое количество сцен
            
        Returns:
            JSON сценария
        """
        lang = language or CONFIG["default_language"]
        
        # Рассчитываем примерное количество слов (средняя скорость речи ~2.5 слова/сек)
        estimated_words = int(target_duration * 2.5)
        
        user_prompt = f"""Create a video script.

TOPIC: {topic}
VOICEOVER LANGUAGE: {lang}
TARGET duration: {target_duration} seconds (approximately {estimated_words} words)"""
        
        if style:
            user_prompt += f"\nSTYLE: {style}"
        
        if num_scenes:
            user_prompt += f"\nNUMBER OF scenes: {num_scenes}"
        
        user_prompt += f"""

### IMPORTANT:
- The total voiceover text volume should be approximately {estimated_words} words.
- Each scene must contain enough text to fully develop the topic.
- Do not make scenes too short - text should be informative and complete.
- Distribute text evenly across all scenes.

Return ONLY JSON without markdown, without explanations, only valid JSON."""
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        # Используем стриминг для длинных ответов
        response = self.client.generate(messages, max_tokens=8192)
        
        if response is None:
            raise ValueError("LLM вернула пустой ответ. Проверьте API ключ и подключение.")
        
        # Извлечение JSON из ответа (убираем markdown code blocks если есть)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
        if response.endswith("```"):
            response = response.rsplit("\n", 1)[0]
        response = response.strip()
        
        # Убираем ```json если есть
        if response.startswith("```json"):
            response = response[7:].strip()
        
        try:
            scenario = json.loads(response)
            return scenario
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ модели (первые 500 символов):\n{response[:500]}...")
            
            # Пытаемся найти JSON в ответе
            json_start = response.find("{")
            json_end = response.rfind("}")
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                try:
                    extracted_json = response[json_start:json_end+1]
                    # Пытаемся исправить обрезанные строки
                    if extracted_json.count('"') % 2 != 0:
                        # Нечетное количество кавычек - обрезанная строка
                        last_quote = extracted_json.rfind('"')
                        if last_quote > 0:
                            extracted_json = extracted_json[:last_quote] + '"}'
                    
                    scenario = json.loads(extracted_json)
                    print("✅ JSON успешно извлечен из ответа (с исправлениями)")
                    return scenario
                except json.JSONDecodeError as e2:
                    print(f"⚠ Не удалось исправить JSON: {e2}")
            
            raise ValueError("Не удалось извлечь валидный JSON из ответа модели. Попробуйте уменьшить количество сцен или длительность.")
    
    def refine_scenario(
        self,
        scenario: dict,
        feedback: str,
    ) -> dict:
        """
        Доработка существующего сценария по фидбеку
        
        Args:
            scenario: Текущий сценарий
            feedback: Фидбек/пожелания по изменению
            
        Returns:
            Обновленный JSON сценария
        """
        user_prompt = f"""Вот текущий сценарий:

```json
{json.dumps(scenario, indent=2, ensure_ascii=False)}
```

Внеси изменения согласно фидбеку: {feedback}

Верни ТОЛЬКО JSON без markdown, без пояснений, только валидный JSON."""
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        response = self.client.generate(messages)
        
        # Извлечение JSON
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
        if response.endswith("```"):
            response = response.rsplit("\n", 1)[0]
        response = response.strip()
        
        if response.startswith("```json"):
            response = response[7:].strip()
        
        try:
            refined = json.loads(response)
            return refined
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ модели:\n{response}")
            raise
    
    def save_scenario(self, scenario: dict, filepath: str):
        """Сохранение сценария в файл"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)
        print(f"✅ Сценарий сохранён: {filepath}")
    
    def load_scenario(self, filepath: str) -> dict:
        """Загрузка сценария из файла"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def print_scenario(self, scenario: dict):
        """Красивый вывод сценария"""
        print("\n" + "="*60)
        print(f"🎬 {scenario.get('metadata', {}).get('vibe', 'Без названия')}")
        print("="*60)
        print(f"📝 Темп: {scenario.get('metadata', {}).get('tempo', '')}")
        print("="*60)
        
        for i, block in enumerate(scenario.get("timeline", [])):
            print(f"\n🎞️  Блок {i+1}")
            print(f"   🎙️  Озвучка: {block.get('voiceover', '')}")
            print(f"   🎨 Фон: {block.get('background', {})}")
            
            overlays = block.get('overlays', [])
            if overlays:
                print(f"   📝 Оверлеи:")
                for overlay in overlays:
                    if isinstance(overlay, dict):
                        print(f"      - {overlay.get('type')}: {overlay.get('text', '')}")
                    else:
                        print(f"      - {overlay}")
            else:
                print(f"   📝 Оверлеи: нет")
        
        if scenario.get("assets_manifest"):
            print(f"\n📌 Ассеты:")
            for asset in scenario.get("assets_manifest", []):
                if isinstance(asset, dict):
                    print(f"   - {asset.get('type')}: {asset.get('name', '')}")
                else:
                    print(f"   - {asset}")
        print("="*60 + "\n")

    def generate_all_assets(
        self,
        topic: str,
        language: str = "ru",
        duration: int = 30,
        style: str = None,
        num_scenes: int = None,
        fast: bool = False,
        use_gpu: bool = True
    ) -> str:
        print("\n📝 Шаг 1: Генерация сценария V2...")
        scenario = self.create_scenario(
            topic=topic,
            language=language,
            target_duration=duration,
            style=style,
            num_scenes=num_scenes
        )
        
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic[:50]).strip()
        video_id = f"{safe_title}_{int(time.time())}"
        video_base_dir = os.path.join(OUTPUT_DIR, video_id)
        
        assets_dir = os.path.join(video_base_dir, "assets")
        audio_dir = os.path.join(video_base_dir, "audio")
        overlays_dir = os.path.join(video_base_dir, "overlays")
        thumbnail_dir = os.path.join(video_base_dir, "thumbnail")
        
        os.makedirs(assets_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(overlays_dir, exist_ok=True)
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        if self.image_generator:
            self.image_generator.output_dir = Path(assets_dir)
        else:
            self.image_generator = ImageGenerator(cookie=self.whisk_cookie, output_dir=assets_dir)
        
        print("\n" + "="*60)
        print(f"🎬 ГЕНЕРАЦИЯ АССЕТОВ V2: {topic}")
        print(f"📂 Папка проекта: {video_base_dir}")
        print("="*60)
        
        scenario_file = os.path.join(video_base_dir, "scenario.json")
        self.save_scenario(scenario, scenario_file)
        self.print_scenario(scenario)
        
        print("\n📦 Шаг 2: Обработка ассетов...")
        assets_map = self._process_assets_manifest(scenario, assets_dir)
        
        print("\n🎨 Шаг 3: Генерация фоновых изображений...")
        background_paths = self._generate_backgrounds(scenario, assets_dir, assets_map)
        
        print("\n🎙️ Шаг 4: Генерация озвучки...")
        audio_paths = self._generate_audio(scenario, audio_dir)
        
        print("\n📝 Шаг 5: Создание оверлеев...")
        overlay_paths = self._create_overlays(scenario, overlays_dir)
        
        print("\n🖼️ Шаг 6: Генерация кликбейтного превью...")
        thumbnail_path = self._generate_thumbnail(topic, scenario.get("style", "mystery"), thumbnail_dir)
        
        print("\n" + "="*60)
        print(f"✅ АССЕТЫ V2 ГОТОВЫ")
        print(f"📂 Папка проекта: {video_base_dir}")
        print(f"📁 assets/: {len(assets_map)} файлов")
        print(f"📁 audio/: {len(audio_paths)} файлов")
        print(f"📁 overlays/: {len(overlay_paths)} файлов")
        if thumbnail_path:
            print(f"🖼️ thumbnail/: 1 файл")
        print("="*60 + "\n")
        
        return video_base_dir

    def _process_assets_manifest(self, scenario: dict, assets_dir: str) -> dict:
        assets_map = {}
        manifest = scenario.get("assets_manifest", [])
        if not manifest:
            print("   ⚠ Assets manifest пуст")
            return assets_map
        
        print(f"   📦 Найдено {len(manifest)} ассетов для обработки")
        
        normalized_manifest = []
        for asset in manifest:
            if isinstance(asset, str):
                normalized_manifest.append({"type": "object", "name": asset, "description": ""})
            elif isinstance(asset, dict):
                normalized_manifest.append(asset)
        
        for asset in normalized_manifest:
            asset_type = asset.get("type", "object")
            asset_name = asset.get("name", "")
            asset_desc = asset.get("description", "")
            if not asset_name:
                continue
            
            print(f"   🔄 Обработка ассета: {asset_name} ({asset_type})")
            asset_found = False
            
            if self.use_stock_photos and self.has_image_search and "pexels" in self.image_search.services:
                try:
                    print(f"   🔍 Поиск стокового фото (Pexels): {asset_name}")
                    results = self.image_search.search(
                        query=asset_desc or asset_name,
                        source="stock",
                        stock_service="pexels",
                        count=1,
                        orientation="landscape"
                    )
                    if results:
                        stock_api = self.image_search.services.get("pexels")
                        if stock_api:
                            asset_path = os.path.join(assets_dir, f"stock_{asset_name.replace(' ', '_')}.jpg")
                            stock_api.download(results[0]["download_url"], asset_path)
                            print(f"   ✅ Найдено стоковое фото")
                            assets_map[asset_name] = asset_path
                            asset_found = True
                except Exception as e:
                    print(f"   ⚠ Не удалось найти стоковое фото: {e}")
            
            if not asset_found and self.use_real_photos and self.has_image_search and "real" in self.image_search.services:
                try:
                    print(f"   📸 Поиск реального фото (DuckDuckGo): {asset_name}")
                    results = self.image_search.search_person(
                        name=asset_name,
                        source="real",
                        count=1
                    )
                    if results:
                        real_api = self.image_search.services.get("real")
                        if real_api:
                            asset_path = os.path.join(assets_dir, f"real_{asset_name.replace(' ', '_')}.jpg")
                            real_api.download(results[0]["download_url"], asset_path)
                            print(f"   ✅ Найдено реальное фото")
                            assets_map[asset_name] = asset_path
                            asset_found = True
                except Exception as e:
                    print(f"   ⚠ Не удалось найти реальное фото: {e}")
            
            if not asset_found:
                print(f"   🎨 Генерация изображения через Whisk...")
                full_prompt = f"{asset_name} {asset_desc}".strip() if asset_desc else asset_name
                clean_prompt = self._clean_prompt_for_whisk(full_prompt, "", asset_type)
                asset_path = self._generate_image_with_whisk(clean_prompt, hash(asset_name) % 10000, assets_dir)
                assets_map[asset_name] = asset_path
        
        return assets_map

    def _clean_prompt_for_whisk(self, prompt: str, description: str, asset_type: str) -> str:
        import re
        prompt_lower = prompt.lower()
        
        if prompt_lower.startswith("generated_image:"):
            prompt = prompt[16:].strip()
            prompt_lower = prompt.lower()
        elif prompt_lower.startswith("stock_video:"):
            prompt = prompt[12:].strip()
            prompt_lower = prompt.lower()
        elif prompt_lower.startswith("stock_photo:"):
            prompt = prompt[12:].strip()
            prompt_lower = prompt.lower()
        elif prompt_lower.startswith("person_photo:"):
            prompt = prompt[13:].strip()
            prompt_lower = prompt.lower()
        
        prominent_names = ["victor surge", "eric knudsen", "slenderman", "slender man", "jeff the killer", "sonic.exe", "herobrine"]
        is_prominent = any(pn in prompt_lower for pn in prominent_names)
        
        if asset_type == "person" and is_prominent:
            return "An anonymous artist working at computer in dark room, mysterious figure"
        if asset_type == "person":
            return f"A person portrait: {prompt}" if prompt else "A person portrait"
        if asset_type == "character":
            return "A tall faceless figure in black suit standing in dark forest, mysterious silhouette, horror style, photorealistic"
        
        clean_prompt = re.sub(r'\([^)]*\)', '', prompt).strip()
        clean_prompt_lower = clean_prompt.lower()
        if any(pn in clean_prompt_lower for pn in prominent_names):
            clean_prompt = "mysterious dark figure, faceless silhouette, horror atmosphere"
        
        if not clean_prompt:
            return f"{asset_type} visualization"
        return clean_prompt

    def _generate_backgrounds(self, scenario: dict, assets_dir: str, assets_map: dict) -> dict:
        background_paths = {}
        timeline = scenario.get("timeline", [])
        for i, block in enumerate(timeline):
            bg = block.get("background", {})
            bg_type = bg.get("type", "generated_image")
            bg_prompt = bg.get("prompt", "")
            
            if not bg_prompt:
                print(f"   ⚠ Блок {i+1}: нет промпта для фона, используем placeholder")
                background_paths[i] = self._create_placeholder_image(i, assets_dir)
                continue
            
            print(f"   🎨 Блок {i+1}: {bg_type} - {bg_prompt[:50]}...")
            try:
                if bg_type == "person_photo":
                    person_name = bg_prompt.split(":")[0] if ":" in bg_prompt else bg_prompt
                    if person_name in assets_map:
                        background_paths[i] = assets_map[person_name]
                        print(f"   ✅ Использовано фото из ассетов")
                        continue
                    if self.use_real_photos and self.has_image_search:
                        print(f"   📸 Поиск реального фото персоны: {person_name}")
                        results = self.image_search.search_person(name=person_name, source="real", count=1)
                        if results:
                            real_api = self.image_search.services.get("real")
                            if real_api:
                                asset_path = os.path.join(assets_dir, f"bg_real_person_{i+1}.jpg")
                                real_api.download(results[0]["download_url"], asset_path)
                                background_paths[i] = asset_path
                                print(f"   ✅ Найдено реальное фото")
                                continue
                
                if bg_type == "stock_photo":
                    if self.use_stock_photos and self.has_image_search and "pexels" in self.image_search.services:
                        print(f"   🔍 Поиск стокового фото (Pexels): {bg_prompt}")
                        results = self.image_search.search(
                            query=bg_prompt, source="stock", stock_service="pexels", count=1, orientation="landscape"
                        )
                        if results:
                            stock_api = self.image_search.services.get("pexels")
                            if stock_api:
                                asset_path = os.path.join(assets_dir, f"bg_stock_{i+1}.jpg")
                                stock_api.download(results[0]["download_url"], asset_path)
                                background_paths[i] = asset_path
                                print(f"   ✅ Найдено стоковое фото")
                                continue
                
                print(f"   ⏳ Генерация изображения через Whisk...")
                clean_bg_prompt = self._clean_prompt_for_whisk(bg_prompt, "", bg_type)
                background_paths[i] = self._generate_image_with_whisk(clean_bg_prompt, i+1, assets_dir)
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                background_paths[i] = self._create_placeholder_image(i, assets_dir)
            time.sleep(2)
        return background_paths

    def _generate_image_with_whisk(self, prompt: str, block_index: int, assets_dir: str) -> str:
        print(f"   ⏳ Генерация изображения для блока {block_index}...")
        saved_paths = self.image_generator.generate(
            prompt=prompt,
            model="IMAGEN_3_5",
            aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
            seed=0,
            count=1
        )
        if saved_paths:
            old_path = saved_paths[0]
            new_path = os.path.join(assets_dir, f"background_{block_index}.png")
            if os.path.exists(old_path):
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(old_path, new_path)
            print(f"   ✅ Изображение сохранено: {new_path}")
            return new_path
        else:
            print(f"   ❌ Ошибка генерации изображения для блока {block_index}")
            return self._create_placeholder_image(block_index - 1, assets_dir)

    def _create_placeholder_image(self, block_index: int, assets_dir: str) -> str:
        img = Image.new("RGB", (1920, 1080), (30, 30, 60))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except:
            font = ImageFont.load_default()
        text = f"Block {block_index + 1}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (1920 - text_w) // 2
        y = (1080 - text_h) // 2
        draw.text((x, y), text, fill="white", font=font)
        path = os.path.join(assets_dir, f"background_{block_index + 1}_placeholder.png")
        img.save(path)
        return path

    def _generate_audio(self, scenario: dict, audio_dir: str) -> dict:
        audio_paths = {}
        timeline = scenario.get("timeline", [])
        for i, block in enumerate(timeline):
            voiceover = block.get("voiceover", "")
            if not voiceover:
                print(f"   ⚠ Блок {i+1}: нет текста озвучки")
                continue
            print(f"   🎙️ Блок {i+1}: {voiceover[:50]}...")
            audio_path = os.path.join(audio_dir, f"block_{i+1}.wav")
            voice_id = "Blake"
            try:
                print(f"  🎙️ Озвучка блока {i+1}...")
                success = tts(text=voiceover, voice_id=voice_id, output_path=audio_path, max_chunk=1000)
                if success:
                    audio_paths[i] = audio_path
                    print(f"   ✅ Аудио сохранено: {audio_path}")
                else:
                    print(f"   ❌ Ошибка генерации аудио для блока {i+1}, создаю тишину")
                    audio_paths[i] = self._create_silence(5, audio_path)
            except Exception as e:
                print(f"   ❌ Ошибка: {e}, создаю тишину")
                audio_paths[i] = self._create_silence(5, audio_path)
            time.sleep(0.5)
        return audio_paths

    def _create_silence(self, duration: float, output_path: str) -> str:
        sample_rate = 48000
        num_samples = int(duration * sample_rate)
        with wave.open(output_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b'\x00\x00' * num_samples)
        return output_path

    def _create_overlays(self, scenario: dict, overlays_dir: str) -> dict:
        overlay_paths = {}
        timeline = scenario.get("timeline", [])
        for i, block in enumerate(timeline):
            overlays = block.get("overlays", [])
            if not overlays:
                continue
            print(f"   📝 Блок {i+1}: создание {len(overlays)} оверлеев...")
            overlay_path = os.path.join(overlays_dir, f"block_{i+1}_overlays.png")
            try:
                self._render_overlays(overlays, overlay_path)
                overlay_paths[i] = overlay_path
                print(f"   ✅ Оверлеи сохранены: {overlay_path}")
            except Exception as e:
                print(f"   ❌ Ошибка создания оверлеев: {e}")
        return overlay_paths

    def _render_overlays(self, overlays: list, output_path: str):
        width, height = 1920, 300
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font_thesis = ImageFont.truetype("arial.ttf", 50)
            font_quote = ImageFont.truetype("arial.ttf", 40)
            font_nameplate = ImageFont.truetype("arial.ttf", 45)
        except:
            font_thesis = ImageFont.load_default()
            font_quote = font_thesis
            font_nameplate = font_thesis
        
        y_offset = 20
        for overlay in overlays:
            overlay_type = overlay.get("type", "thesis")
            text = overlay.get("text", "")
            if not text:
                continue
            
            if overlay_type == "thesis":
                bbox = draw.textbbox((0, 0), text, font=font_thesis)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                x = (width - text_w) // 2
                y = y_offset
                padding = 20
                draw.rounded_rectangle(
                    [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                    radius=15, fill=(0, 0, 0, 180)
                )
                draw.text((x, y), text, fill="white", font=font_thesis)
                y_offset += text_h + padding * 2 + 10
            elif overlay_type == "quote":
                quote_text = f"❝ {text} ❞"
                bbox = draw.textbbox((0, 0), quote_text, font=font_quote)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                x = (width - text_w) // 2
                y = y_offset
                padding = 15
                draw.rounded_rectangle(
                    [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                    radius=10, fill=(255, 255, 200, 150)
                )
                draw.text((x, y), quote_text, fill=(50, 50, 50), font=font_quote)
                y_offset += text_h + padding * 2 + 10
            elif overlay_type == "nameplate":
                bbox = draw.textbbox((0, 0), text, font=font_nameplate)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                x = (width - text_w) // 2
                y = y_offset
                padding = 15
                draw.rounded_rectangle(
                    [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                    radius=10, fill=(100, 100, 200, 200)
                )
                draw.text((x, y), text, fill="white", font=font_nameplate)
                y_offset += text_h + padding * 2 + 10
        img.save(output_path, "PNG")

    def _generate_thumbnail(self, topic: str, style: str, thumbnail_dir: str) -> str:
        if not self.thumbnail_generator:
            print("   ⚠ Генератор превью не инициализирован (нет Whisk cookie)")
            return None
        try:
            original_dir = self.thumbnail_generator.output_dir
            self.thumbnail_generator.output_dir = thumbnail_dir
            thumbnail_path = self.thumbnail_generator.generate_thumbnail(topic=topic)
            self.thumbnail_generator.output_dir = original_dir
            return thumbnail_path
        except Exception as e:
            print(f"   ⚠ Ошибка генерации превью: {e}")
            return None


def create_scenario_cli():
    """CLI для создания сценария или полного видео"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Генератор видео-сценариев V2 через Fireworks AI")
    parser.add_argument("topic", nargs="?", help="Тема видео")
    parser.add_argument("--api-key", help="Fireworks API key")
    parser.add_argument("--language", "-l", default="en", help="Language (en, ru)")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Целевая длительность (сек)")
    parser.add_argument("--style", "-s", help="Стиль видео")
    parser.add_argument("--scenes", "-n", type=int, help="Количество сцен")
    parser.add_argument("--output", "-o", help="Файл для сохранения сценария (JSON)")
    parser.add_argument("--refine", "-r", help="Файл сценария для доработки")
    parser.add_argument("--feedback", "-f", help="Фидбек для доработки сценария")
    parser.add_argument("--generate-all", action="store_true", help="Генерировать все ассеты (без сборки видео)")
    parser.add_argument("--whisk-cookie", help="Whisk cookie для генерации изображений")
    parser.add_argument("--pexels-key", help="Pexels API key для стоковых фото")
    parser.add_argument("--use-stock", action="store_true", help="Использовать стоковые фото Pexels")
    parser.add_argument("--no-real", action="store_true", help="Не использовать реальные фото")
    
    args = parser.parse_args()
    
    topic = args.topic
    if not topic:
        topic = input("🎬 Введите тему видео: ").strip()
        if not topic:
            print("❌ Тема не может быть пустой")
            return
    
    fireworks_key = args.api_key or os.environ.get("FIREWORKS_API_KEY")
    whisk_cookie = args.whisk_cookie or os.environ.get("WHISK_COOKIE")
    pexels_key = args.pexels_key or os.environ.get("PEXELS_API_KEY")
    
    planner = VideoScenarioPlannerV2(
        api_key=fireworks_key,
        whisk_cookie=whisk_cookie,
        pexels_api_key=pexels_key,
        use_real_photos=not args.no_real,
        use_stock_photos=args.use_stock
    )
    
    if args.refine and args.feedback:
        print(f"📝 Доработка сценария: {args.refine}")
        scenario = planner.load_scenario(args.refine)
        scenario = planner.refine_scenario(scenario, args.feedback)
        planner.print_scenario(scenario)
        output_file = args.output or f"scenario_v2_{topic[:30].replace(' ', '_')}.json"
        planner.save_scenario(scenario, output_file)
    elif args.generate_all:
        print(f"🎬 Генерация ассетов V2: {topic}")
        assets_path = planner.generate_all_assets(
            topic=topic,
            language=args.language,
            duration=args.duration,
            style=args.style,
            num_scenes=args.scenes
        )
        print(f"\n🎉 Ассеты V2 готовы: {assets_path}")
    else:
        print(f"🎬 Создание сценария: {topic}")
        scenario = planner.create_scenario(
            topic=topic,
            language=args.language,
            target_duration=args.duration,
            style=args.style,
            num_scenes=args.scenes,
        )
        planner.print_scenario(scenario)
        output_file = args.output or f"scenario_v2_{topic[:30].replace(' ', '_')}.json"
        planner.save_scenario(scenario, output_file)


if __name__ == "__main__":
    create_scenario_cli()

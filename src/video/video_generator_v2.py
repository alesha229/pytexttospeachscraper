"""
Генератор видео V2 из сценария нового формата
Автоматизирует процесс создания видео с новым пайплайном:
1. Генерирует сценарий через Fireworks AI (V2 формат)
2. Создает/находит изображения для каждого блока (background)
3. Генерирует озвучку через InWorld TTS
4. Добавляет оверлеи (тезисы, цитаты, плашки с именами)
5. Собирает всё в видео через moviepy

Использование:
    python video_generator_v2.py "Тема видео"
    python video_generator_v2.py "Тема" --duration 60 --scenes 5
    python video_generator_v2.py --topic "Тема" --language en --style cinematic

Вход:
    - topic (str): Тема видео (обязательно)
    - language (str): Язык озвучки (по умолчанию "ru")
    - duration (int): Длительность в секундах (по умолчанию 30)
    - style (str): Стиль видео (опционально)
    - scenes (int): Количество сцен (опционально)
    - fireworks-key (str): Fireworks API key (или через FIREWORKS_API_KEY)
    - whisk-cookie (str): Whisk cookie (или через WHISK_COOKIE)

Выход:
    - Папка в video_output/{topic}_{timestamp}/:
        - scenario.json (сценарий V2)
        - assets/ (изображения и ассеты)
        - audio/ (аудио озвучки)
        - overlays/ (текстовые оверлеи)
        - videos/ (финальное видео)
"""

import os
import sys
import json
import time
from typing import Optional, Dict, List
from pathlib import Path

from src.planning import VideoScenarioPlannerV2
from src.images import ImageGenerator, WhiskAPI
from src.images import ImageSearch
from src.images import ImageValidator
from src.tts import tts, COOKIES as TTS_COOKIES
from src.video.video_assembler_fast import FastVideoAssembler, VideoScene
from src.images import ThumbnailGenerator
from src.config import WHISK_COOKIE, IMAGE_OUTPUT_DIR
from PIL import Image, ImageDraw, ImageFont
import wave

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "video_output_v2")

os.makedirs(OUTPUT_DIR, exist_ok=True)


class VideoGeneratorV2:
    """Генератор видео V2 из текстового описания с новым пайплайном"""
    
    def __init__(
        self,
        fireworks_api_key: str = None,
        whisk_cookie: str = None,
        inworld_cookies: dict = None,
        pexels_api_key: str = None,
        use_real_photos: bool = True,
        use_stock_photos: bool = False,
        validate_images: bool = True
    ):
        """
        Инициализация генератора
        
        Args:
            fireworks_api_key: API ключ для Fireworks AI
            whisk_cookie: Cookie для Whisk API (Google Labs)
            inworld_cookies: Cookies для InWorld TTS
            pexels_api_key: API ключ для Pexels (сток)
            use_real_photos: Использовать реальные фото/скриншоты (DuckDuckGo)
            use_stock_photos: Использовать стоковые фото (Pexels)
            validate_images: Валидировать изображения через Qwen VL
        """
        self.fireworks_api_key = fireworks_api_key
        self.whisk_cookie = whisk_cookie or os.environ.get("WHISK_COOKIE", "")
        self.inworld_cookies = inworld_cookies
        self.use_real_photos = use_real_photos
        self.use_stock_photos = use_stock_photos
        self.validate_images = validate_images
        
        self.scenario_planner = VideoScenarioPlannerV2(api_key=fireworks_api_key)
        self.image_generator = None
        self.video_assembler = None
        self.fast_assembler = None
        self.thumbnail_generator = None
        
        # Инициализируем генератор превью
        if self.whisk_cookie:
            self.thumbnail_generator = ThumbnailGenerator(
                whisk_cookie=self.whisk_cookie,
                output_dir=os.path.join(OUTPUT_DIR, "thumbnails")
            )
        
        # Инициализируем валидатор изображений
        self.validator = None
        if self.validate_images and self.fireworks_api_key:
            try:
                self.validator = ImageValidator(api_key=self.fireworks_api_key)
                print("   ✅ Валидатор изображений (Qwen VL) инициализирован")
            except ValueError:
                self.validator = None
                print("   ⚠ Не удалось инициализировать валидатор (нет API ключа)")
        
        # Инициализируем поиск изображений
        try:
            self.image_search = ImageSearch(
                pexels_key=pexels_api_key,
                use_duckduckgo=use_real_photos,
                validator=self.validator
            )
            self.has_image_search = True
        except ValueError:
            self.image_search = None
            self.has_image_search = False
            print("⚠ Не удалось инициализировать поиск изображений.")
            print("   Будет использоваться только генерация через Whisk.")
    
    def generate_video(
        self,
        topic: str,
        language: str = "ru",
        duration: int = 30,
        style: str = None,
        num_scenes: int = None,
        video_filename: str = None,
        fast: bool = False,
        use_gpu: bool = True
    ) -> str:
        """
        Полный цикл генерации видео из темы
        
        Args:
            topic: Тема видео
            language: Язык озвучки
            duration: Длительность в секундах
            style: Стиль видео
            num_scenes: Количество сцен
            video_filename: Имя выходного файла
            
        Returns:
            Путь к созданному видео
        """
        # Шаг 1: Генерация сценария V2
        print("\n📝 Шаг 1: Генерация сценария V2...")
        scenario = self.scenario_planner.create_scenario(
            topic=topic,
            language=language,
            target_duration=duration,
            style=style,
            num_scenes=num_scenes
        )
        
        # Создаем папку для конкретного видео
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic[:50]).strip()
        video_id = f"{safe_title}_{int(time.time())}"
        video_base_dir = os.path.join(OUTPUT_DIR, video_id)
        
        assets_dir = os.path.join(video_base_dir, "assets")
        audio_dir = os.path.join(video_base_dir, "audio")
        overlays_dir = os.path.join(video_base_dir, "overlays")
        videos_dir = os.path.join(video_base_dir, "videos")
        
        os.makedirs(assets_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(overlays_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)
        
        # Инициализируем генераторы
        self.image_generator = ImageGenerator(cookie=self.whisk_cookie, output_dir=assets_dir)
        self.fast_assembler = FastVideoAssembler(output_dir=videos_dir)
        
        print("\n" + "="*60)
        print(f"🎬 ГЕНЕРАЦИЯ ВИДЕО V2: {topic}")
        print(f"📂 Папка проекта: {video_base_dir}")
        if self.has_image_search:
            print(f"🔍 Поиск изображений: ✅")
            print(f"   - Реальные фото/скриншоты: DuckDuckGo ✅")
        else:
            print(f"🔍 Поиск изображений: ❌ (нет API ключей)")
        print("="*60)
        
        scenario_file = os.path.join(video_base_dir, "scenario.json")
        self.scenario_planner.save_scenario(scenario, scenario_file)
        self.scenario_planner.print_scenario(scenario)
        
        # Шаг 2: Обработка ассетов из assets_manifest
        print("\n📦 Шаг 2: Обработка ассетов...")
        assets_map = self._process_assets_manifest(scenario, assets_dir)
        
        # Шаг 2+3 параллельно: озвучка в фоне, фоны в основном потоке
        from concurrent.futures import ThreadPoolExecutor, Future
        
        audio_future = None
        with ThreadPoolExecutor(max_workers=1) as audio_pool:
            print("\n🎙️ Запуск озвучки в фоне...")
            audio_future = audio_pool.submit(self._generate_audio, scenario, audio_dir)
            
            # Шаг 3: Генерация фоновых изображений (в основном потоке)
            print("\n🎨 Шаг 3: Генерация фоновых изображений...")
            background_paths = self._generate_backgrounds(scenario, assets_dir, assets_map)
        
        # Дожидаемся озвучку если ещё не готова
        print("\n🎙️ Ожидание завершения озвучки...")
        audio_paths = audio_future.result() if audio_future else {}
        
        # Шаг 4 (пропускаем — уже сделано параллельно)
        
        # Шаг 5: Создание оверлеев
        print("\n📝 Шаг 5: Создание оверлеев...")
        overlay_paths = self._create_overlays(scenario, overlays_dir)
        
        # Шаг 6: Сборка видео
        print("\n🎬 Шаг 6: Сборка видео...")
        video_path = self._assemble_video(
            scenario, 
            background_paths, 
            audio_paths, 
            overlay_paths,
            videos_dir, 
            video_filename,
            fast=fast,
            use_gpu=use_gpu
        )
        
        # Шаг 7: Генерация превью
        print("\n🖼️ Шаг 7: Генерация кликбейтного превью...")
        thumbnail_path = self._generate_thumbnail(topic, scenario.get("style", "mystery"), video_base_dir)
        
        print("\n" + "="*60)
        print(f"✅ ВИДЕО V2 ГОТОВО: {video_path}")
        if thumbnail_path:
            print(f"🖼️ ПРЕВЬЮ ГОТОВО: {thumbnail_path}")
        print("="*60 + "\n")
        
        return video_path
    
    def _download_first_available(self, results: list, api, save_path: str) -> Optional[str]:
        """Пробует скачать изображения по очереди, пока одно не получится."""
        for idx, result in enumerate(results):
            url = result.get("download_url", "")
            if not url:
                continue
            try:
                api.download(url, save_path)
                return save_path
            except Exception as e:
                print(f"      ⚠ Ошибка скачивания ({idx+1}/{len(results)}): {e}")
                continue
        return None

    def _search_person_photo(self, name: str, desc: str, assets_dir: str, filename_prefix: str) -> Optional[str]:
        """
        Ищет фото персоны из интернета с несколькими попытками и разными запросами.
        Для персон НИКОГДА не используется Whisk (запрещает генерацию личностей).
        """
        queries = [
            desc or name,
            name,
            f"{name} portrait",
            f"{name} photo",
        ]
        seen = set(q.lower() for q in queries)
        
        parts = name.strip().split()
        if len(parts) >= 2:
            extra = [f"{parts[0]} {parts[-1]}", f"{parts[-1]} {parts[0]}"]
            for q in extra:
                if q.lower() not in seen:
                    queries.append(q)
                    seen.add(q.lower())
        
        for qi, search_query in enumerate(queries):
            if not search_query:
                continue
            print(f"   📸 Попытка {qi+1}/{len(queries)}: '{search_query}'")
            try:
                if self.use_real_photos and self.has_image_search and "real" in self.image_search.services:
                    results = self.image_search.search_person(
                        name=search_query,
                        source="real",
                        count=1
                    )
                    if results:
                        real_api = self.image_search.services.get("real")
                        if real_api:
                            asset_path = os.path.join(assets_dir, f"{filename_prefix}.jpg")
                            downloaded = self._download_first_available(results, real_api, asset_path)
                            if downloaded:
                                print(f"   ✅ Найдено фото персоны (попытка {qi+1})")
                                return downloaded
                
                if self.use_stock_photos and self.has_image_search and "pexels" in self.image_search.services:
                    results = self.image_search.search(
                        query=search_query,
                        source="stock",
                        stock_service="pexels",
                        count=1,
                        orientation="portrait"
                    )
                    if results:
                        stock_api = self.image_search.services.get("pexels")
                        if stock_api:
                            asset_path = os.path.join(assets_dir, f"{filename_prefix}.jpg")
                            downloaded = self._download_first_available(results, stock_api, asset_path)
                            if downloaded:
                                print(f"   ✅ Найдено стоковое фото персоны (попытка {qi+1})")
                                return downloaded
            except Exception as e:
                print(f"   ⚠ Ошибка поиска (попытка {qi+1}): {e}")
        
        print(f"   ❌ Не удалось найти фото персоны из интернета")
        return None

    def _process_assets_manifest(self, scenario: dict, assets_dir: str) -> dict:
        """
        Обрабатывает assets_manifest для предварительной загрузки ассетов
        Приоритет: 
          - person: ТОЛЬКО интернет (DuckDuckGo/Pexels), Whisk запрещает генерацию личностей
          - остальные: сток (Pexels) > реальные (DuckDuckGo) > генерация Whisk
        """
        assets_map = {}
        manifest = scenario.get("assets_manifest", [])
        
        if not manifest:
            print("   ⚠ Assets manifest пуст")
            return assets_map
        
        print(f"   📦 Найдено {len(manifest)} ассетов для обработки")
        
        normalized_manifest = []
        for asset in manifest:
            if isinstance(asset, str):
                normalized_manifest.append({
                    "type": "object",
                    "name": asset,
                    "description": "",
                    "search_query": ""
                })
            elif isinstance(asset, dict):
                normalized_manifest.append(asset)
        
        for asset in normalized_manifest:
            asset_type = asset.get("type", "object")
            asset_name = asset.get("name", "")
            asset_desc = asset.get("description", "")
            search_query = asset.get("search_query", "")
            
            if not asset_name:
                continue
            
            safe_file_name = self._safe_asset_filename(search_query or asset_name)
            
            print(f"   🔄 Обработка ассета: {asset_name} ({asset_type})")
            if search_query:
                print(f"      🔍 Search query: {search_query}")
            
            asset_found = False
            
            # person — ТОЛЬКО из интернета, Whisk не подходит
            if asset_type == "person":
                prefix = f"person_{safe_file_name}"
                result = self._search_person_photo(search_query or asset_name, asset_desc, assets_dir, prefix)
                if result:
                    assets_map[asset_name] = result
                    asset_found = True
                else:
                    print(f"   🖼️ Создаю плейсхолдер для персоны")
                    assets_map[asset_name] = self._create_person_placeholder(asset_name, asset_desc, assets_dir)
                    asset_found = True
            
            # Не-person: сток > DuckDuckGo > Whisk
            if not asset_found:
                if self.use_stock_photos and self.has_image_search and "pexels" in self.image_search.services:
                    try:
                        search_term = search_query or asset_desc or asset_name
                        print(f"   🔍 Поиск стокового фото (Pexels): {search_term}")
                        results = self.image_search.search(
                            query=search_term,
                            source="stock",
                            stock_service="pexels",
                            count=1,
                            orientation="landscape"
                        )
                        if results:
                            stock_api = self.image_search.services.get("pexels")
                            if stock_api:
                                asset_path = os.path.join(assets_dir, f"stock_{safe_file_name}.jpg")
                                downloaded = self._download_first_available(results, stock_api, asset_path)
                                if downloaded:
                                    print(f"   ✅ Найдено стоковое фото")
                                    assets_map[asset_name] = downloaded
                                    asset_found = True
                                else:
                                    print(f"   ⚠ Ни одно стоковое фото не скачалось")
                    except Exception as e:
                        print(f"   ⚠ Не удалось найти стоковое фото: {e}")
                
                if not asset_found and self.use_real_photos and self.has_image_search and "real" in self.image_search.services:
                    try:
                        search_term = search_query or asset_desc or asset_name
                        print(f"   📸 Поиск реального фото (DuckDuckGo): {search_term}")
                        if asset_type == "location":
                            results = self.image_search.search_location(
                                name=search_term,
                                source="real",
                                count=1
                            )
                        else:
                            results = self.image_search.search(
                                query=search_term,
                                source="real",
                                count=1
                            )
                        if results:
                            real_api = self.image_search.services.get("real")
                            if real_api:
                                asset_path = os.path.join(assets_dir, f"real_{safe_file_name}.jpg")
                                downloaded = self._download_first_available(results, real_api, asset_path)
                                if downloaded:
                                    print(f"   ✅ Найдено реальное фото")
                                    assets_map[asset_name] = downloaded
                                    asset_found = True
                                else:
                                    print(f"   ⚠ Ни одно реальное фото не скачалось")
                    except Exception as e:
                        print(f"   ⚠ Не удалось найти реальное фото: {e}")
            
            if not asset_found:
                print(f"   🎨 Генерация изображения через Whisk...")
                clean_prompt = self._clean_prompt_for_whisk(asset_name, asset_desc, asset_type)
                asset_path = self._generate_image_with_whisk(clean_prompt, hash(asset_name) % 10000, assets_dir, asset_type=asset_type)
                assets_map[asset_name] = asset_path
        
        return assets_map

    def _safe_asset_filename(self, name: str) -> str:
        """Создает безопасное английское имя файла из search_query или name"""
        import re
        safe = re.sub(r'[^a-zA-Z0-9_\s]', '', name)
        safe = re.sub(r'\s+', ' ', safe).strip()
        if not safe:
            safe = f"asset_{abs(hash(name)) % 10000}"
        return safe.replace(' ', '_')

    def _clean_prompt_for_whisk(self, name: str, description: str, asset_type: str) -> str:
        """
        Очищает промпт от специфических имен и технических деталей для Whisk API.
        Whisk не любит имена людей в промптах (ошибка PUBLIC_ERROR_PROMINENT_PEOPLE_FILTER_FAILED).
        """
        import re
        
        # Список известных имен которые нужно заменять
        prominent_names = [
            "victor surge", "eric knudsen", "slenderman", "slender man",
            "jeff the killer", "sonic.exe", "herobrine"
        ]
        
        # Проверяем имя
        name_lower = name.lower()
        is_prominent = any(pn in name_lower for pn in prominent_names)
        
        # Для персон с известными именами - полностью заменяем
        if asset_type == "person" and is_prominent:
            return f"An anonymous artist working at computer in dark room, mysterious figure"
        
        # Для остальных персон
        if asset_type == "person":
            return f"A person portrait: {description}" if description else "A person portrait"
        
        # Для character типа
        if asset_type == "character":
            return f"A tall faceless figure in black suit standing in dark forest, mysterious silhouette, horror style, photorealistic"
        
        # Для остальных типов чистим скобки и имена
        clean_name = re.sub(r'\([^)]*\)', '', name).strip()
        clean_desc = re.sub(r'\([^)]*\)', '', description).strip()
        
        # Проверяем описание на известные имена
        desc_lower = clean_desc.lower()
        if any(pn in desc_lower for pn in prominent_names):
            clean_desc = "mysterious dark figure, faceless silhouette, horror atmosphere"
        
        if not clean_name:
            return f"{asset_type}: {clean_desc}" if clean_desc else f"{asset_type}"
        
        return f"{asset_type}: {clean_name}. {clean_desc}"

    def _create_person_placeholder(self, name: str, description: str, assets_dir: str) -> str:
        """Создает placeholder для персоны"""
        img = Image.new("RGB", (1920, 1080), (40, 40, 60))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 60)
            font_small = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        # Рисуем круг для аватара
        center_x, center_y = 960, 400
        radius = 150
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            fill=(80, 80, 100)
        )
        
        # Имя
        text = name
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(((1920 - text_w) // 2, 600), text, fill="white", font=font)
        
        # Описание
        if description:
            bbox = draw.textbbox((0, 0), description, font=font_small)
            text_w = bbox[2] - bbox[0]
            draw.text(((1920 - text_w) // 2, 680), description, fill=(200, 200, 200), font=font_small)
        
        path = os.path.join(assets_dir, f"person_{name.replace(' ', '_')}_placeholder.png")
        img.save(path)
        return path
    
    def _create_location_placeholder(self, name: str, description: str, assets_dir: str) -> str:
        """Создает placeholder для локации"""
        img = Image.new("RGB", (1920, 1080), (30, 60, 30))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        text = f"📍 {name}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x = (1920 - text_w) // 2
        y = (1080 - text_h) // 2
        
        draw.text((x, y), text, fill="white", font=font)
        
        path = os.path.join(assets_dir, f"location_{name.replace(' ', '_')}_placeholder.png")
        img.save(path)
        return path
    
    def _create_object_placeholder(self, name: str, description: str, assets_dir: str) -> str:
        """Создает placeholder для объекта"""
        img = Image.new("RGB", (1920, 1080), (60, 30, 30))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        text = f"🎯 {name}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x = (1920 - text_w) // 2
        y = (1080 - text_h) // 2
        
        draw.text((x, y), text, fill="white", font=font)
        
        path = os.path.join(assets_dir, f"object_{name.replace(' ', '_')}_placeholder.png")
        img.save(path)
        return path
    
    def _generate_backgrounds(self, scenario: dict, assets_dir: str, assets_map: dict) -> dict:
        """
        Генерирует фоновые изображения для всех блоков timeline
        person_photo: ТОЛЬКО из интернета (Whisk запрещает личности)
        Остальные: генерация Whisk > реальные фото > сток
        """
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
                # 1. person_photo — ТОЛЬКО интернет, без Whisk
                if bg_type == "person_photo":
                    person_name = bg_prompt.split(":")[0] if ":" in bg_prompt else bg_prompt
                    
                    if person_name in assets_map:
                        background_paths[i] = assets_map[person_name]
                        print(f"   ✅ Использовано фото из ассетов")
                        continue
                    
                    search_term = block.get("overlays", [{}])[0].get("search_query", person_name) if block.get("overlays") else person_name
                    result = self._search_person_photo(
                        search_term or person_name, bg_prompt, assets_dir,
                        f"bg_person_{i+1}"
                    )
                    if result:
                        background_paths[i] = result
                        continue
                    
                    print(f"   🖼️ Создаю плейсхолдер для персоны")
                    background_paths[i] = self._create_person_placeholder(person_name, bg_prompt, assets_dir)
                    continue
                
                # 2. stock_photo
                if bg_type == "stock_photo":
                    if self.use_stock_photos and self.has_image_search and "pexels" in self.image_search.services:
                        print(f"   🔍 Поиск стокового фото (Pexels): {bg_prompt}")
                        results = self.image_search.search(
                            query=bg_prompt,
                            source="stock",
                            stock_service="pexels",
                            count=1,
                            orientation="landscape"
                        )
                        if results:
                            stock_api = self.image_search.services.get("pexels")
                            if stock_api:
                                asset_path = os.path.join(assets_dir, f"bg_stock_{i+1}.jpg")
                                downloaded = self._download_first_available(results, stock_api, asset_path)
                                if downloaded:
                                    background_paths[i] = downloaded
                                    print(f"   ✅ Найдено стоковое фото")
                                    continue
                        print(f"   ⚠ Стоковое фото не скачалось, генерируем...")
                
                # 3. generated_image или fallback — Whisk
                print(f"   ⏳ Генерация изображения через Whisk...")
                clean_bg_prompt = self._clean_prompt_for_whisk(bg_prompt.split(":")[0] if ":" in bg_prompt else "", bg_prompt, bg_type)
                background_paths[i] = self._generate_image_with_whisk(clean_bg_prompt, i+1, assets_dir, asset_type=bg_type)
                
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                background_paths[i] = self._create_placeholder_image(i, assets_dir)
            
            time.sleep(2)
        
        return background_paths
    
    def _generate_image_with_whisk(self, prompt: str, block_index: int, assets_dir: str, asset_type: str = None) -> str:
        """Генерирует изображение через Whisk API. При ошибке фильтра персон — повтор с обобщённым промптом."""
        print(f"   ⏳ Генерация изображения для блока {block_index}...")
        try:
            saved_paths = self.image_generator.generate(
                prompt=prompt,
                model="IMAGEN_3_5",
                aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
                seed=0,
                count=1
            )
        except Exception as e:
            err = str(e).upper()
            if "PROMINENT_PEOPLE" in err or "PEOPLE_FILTER" in err or "PUBLIC_ERROR" in err:
                print(f"   ⚠ Whisk заблокировал промпт (фильтр персон), повтор без имени...")
                generic = self._anonymize_prompt(prompt, asset_type)
                if generic != prompt:
                    try:
                        saved_paths = self.image_generator.generate(
                            prompt=generic,
                            model="IMAGEN_3_5",
                            aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
                            seed=0,
                            count=1
                        )
                    except Exception as e2:
                        print(f"   ⚠ Повторная генерация тоже заблокирована: {e2}")
                        saved_paths = []
                else:
                    saved_paths = []
            elif "400" in str(e):
                print(f"   ⚠ Whisk 400 ошибка, повтор с упрощённым промптом...")
                simplified = self._simplify_prompt(prompt)
                try:
                    saved_paths = self.image_generator.generate(
                        prompt=simplified,
                        model="IMAGEN_3_5",
                        aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
                        seed=0,
                        count=1
                    )
                except Exception as e2:
                    print(f"   ⚠ Упрощённый промпт тоже не прошёл: {e2}")
                    saved_paths = []
            else:
                print(f"   ❌ Ошибка генерации Whisk: {e}")
                return self._create_placeholder_image(block_index - 1, assets_dir)
        
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
    
    def _anonymize_prompt(self, prompt: str, asset_type: str = None) -> str:
        """Заменяет конкретные имена в промпте на обобщённое описание."""
        import re
        if asset_type == "person" or asset_type == "person_photo":
            return "A professional portrait of a person in a studio setting, neutral background, photorealistic"
        
        if ":" in prompt:
            after_colon = ":".join(prompt.split(":")[1:]).strip()
            if after_colon:
                return after_colon
        
        prompt = re.sub(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', 'a person', prompt)
        return prompt
    
    def _simplify_prompt(self, prompt: str) -> str:
        """Упрощает промпт для Whisk — убирает сложные конструкции."""
        import re
        simplified = re.sub(r'[^\w\s,.-]', '', prompt)
        words = simplified.split()
        if len(words) > 20:
            simplified = ' '.join(words[:20])
        return simplified.strip()
    
    def _create_stock_placeholder(self, prompt: str, assets_dir: str) -> str:
        """Создает placeholder для stock video"""
        img = Image.new("RGB", (1920, 1080), (20, 20, 40))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 50)
        except:
            font = ImageFont.load_default()
        
        text = f"🎬 Stock: {prompt[:50]}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x = (1920 - text_w) // 2
        y = (1080 - text_h) // 2
        
        draw.text((x, y), text, fill=(150, 150, 200), font=font)
        
        path = os.path.join(assets_dir, f"stock_{hash(prompt) % 10000}_placeholder.png")
        img.save(path)
        return path
    
    def _create_placeholder_image(self, block_index: int, assets_dir: str) -> str:
        """Создает изображение-заглушку"""
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
        """
        Генерирует аудио для всех блоков timeline
        
        Returns:
            Dict {block_index: audio_path}
        """
        audio_paths = {}
        timeline = scenario.get("timeline", [])
        
        for i, block in enumerate(timeline):
            voiceover = block.get("voiceover", "")
            
            if not voiceover:
                print(f"   ⚠ Блок {i+1}: нет текста озвучки")
                continue
            
            print(f"   🎙️ Блок {i+1}: {voiceover[:50]}...")
            
            # Путь к аудиофайлу
            audio_path = os.path.join(audio_dir, f"block_{i+1}.wav")
            
            # Используем русский голос
            voice_id = "Blake"
            
            try:
                print(f"  🎙️ Озвучка блока {i+1}...")
                success = tts(
                    text=voiceover,
                    voice_id=voice_id,
                    output_path=audio_path,
                    max_chunk=1000
                )
                
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
        """Создаёт тишину заданной длительности"""
        sample_rate = 48000
        num_samples = int(duration * sample_rate)
        
        with wave.open(output_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b'\x00\x00' * num_samples)
        
        return output_path
    
    def _create_overlays(self, scenario: dict, overlays_dir: str) -> dict:
        """
        Создает изображения оверлеев для всех блоков
        
        Returns:
            Dict {block_index: overlay_path}
        """
        overlay_paths = {}
        timeline = scenario.get("timeline", [])
        
        for i, block in enumerate(timeline):
            overlays = block.get("overlays", [])
            
            if not overlays:
                continue
            
            print(f"   📝 Блок {i+1}: создание {len(overlays)} оверлеев...")
            
            # Создаем одно изображение со всеми оверлеями
            overlay_path = os.path.join(overlays_dir, f"block_{i+1}_overlays.png")
            
            try:
                self._render_overlays(overlays, overlay_path)
                overlay_paths[i] = overlay_path
                print(f"   ✅ Оверлеи сохранены: {overlay_path}")
            except Exception as e:
                print(f"   ❌ Ошибка создания оверлеев: {e}")
        
        return overlay_paths
    
    def _render_overlays(self, overlays: list, output_path: str):
        """Рендерит оверлеи в изображение"""
        # Определяем размер изображения
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
                # Тезис - крупный текст по центру
                bbox = draw.textbbox((0, 0), text, font=font_thesis)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                x = (width - text_w) // 2
                y = y_offset
                
                # Фон под текст
                padding = 20
                draw.rounded_rectangle(
                    [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                    radius=15,
                    fill=(0, 0, 0, 180)
                )
                
                draw.text((x, y), text, fill="white", font=font_thesis)
                y_offset += text_h + padding * 2 + 10
                
            elif overlay_type == "quote":
                # Цитата - курсив с кавычками
                quote_text = f"❝ {text} ❞"
                bbox = draw.textbbox((0, 0), quote_text, font=font_quote)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                x = (width - text_w) // 2
                y = y_offset
                
                # Фон под текст
                padding = 15
                draw.rounded_rectangle(
                    [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                    radius=10,
                    fill=(255, 255, 200, 150)
                )
                
                draw.text((x, y), quote_text, fill=(50, 50, 50), font=font_quote)
                y_offset += text_h + padding * 2 + 10
                
            elif overlay_type == "nameplate":
                # Плашка с именем
                bbox = draw.textbbox((0, 0), text, font=font_nameplate)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                x = (width - text_w) // 2
                y = y_offset
                
                # Фон под текст
                padding = 15
                draw.rounded_rectangle(
                    [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                    radius=10,
                    fill=(100, 100, 200, 200)
                )
                
                draw.text((x, y), text, fill="white", font=font_nameplate)
                y_offset += text_h + padding * 2 + 10
        
        # Сохраняем
        img.save(output_path, "PNG")
    
    def _assemble_video(
        self,
        scenario: dict,
        background_paths: dict,
        audio_paths: dict,
        overlay_paths: dict,
        videos_dir: str,
        video_filename: str = None,
        fast: bool = False,
        use_gpu: bool = True
    ) -> str:
        """Собирает видео из фонов, аудио и оверлеев"""
        scenes = []
        timeline = scenario.get("timeline", [])
        
        for i, block in enumerate(timeline):
            bg_path = background_paths.get(i)
            audio_path = audio_paths.get(i)
            
            if not bg_path or not audio_path:
                print(f"   ⚠ Блок {i+1}: отсутствуют файлы, пропускаем")
                continue
            
            # Определяем длительность по аудио
            try:
                with wave.open(audio_path, 'rb') as wf:
                    duration = wf.getnframes() / wf.getframerate()
            except:
                duration = 5
            
            overlay_path = overlay_paths.get(i)
            
            scenes.append(VideoScene(
                image_path=bg_path,
                audio_path=audio_path,
                voiceover_text=block.get("voiceover", ""),
                duration=duration,
                scene_number=i+1,
                overlay_path=overlay_path
            ))
        
        if not video_filename:
            video_filename = "video_v2.mp4"
        
        return self.fast_assembler.assemble_video(
            scenes,
            output_filename=video_filename,
            fps=24,
            use_gpu=use_gpu,
            fast=fast
        )
    
    def _generate_thumbnail(self, topic: str, style: str, video_base_dir: str) -> str:
        """Генерирует кликбейтное превью для видео"""
        if not self.thumbnail_generator:
            print("   ⚠ Генератор превью не инициализирован (нет Whisk cookie)")
            return None
        
        try:
            # Создаем папку для превью внутри проекта
            thumbnail_dir = os.path.join(video_base_dir, "thumbnail")
            os.makedirs(thumbnail_dir, exist_ok=True)
            
            # Временно меняем output_dir
            original_dir = self.thumbnail_generator.output_dir
            self.thumbnail_generator.output_dir = thumbnail_dir
            
            # Передаем ТОЛЬКО тему - AI сам определит стиль по ключевым словам
            thumbnail_path = self.thumbnail_generator.generate_thumbnail(
                topic=topic
            )
            
            # Возвращаем output_dir обратно
            self.thumbnail_generator.output_dir = original_dir
            
            return thumbnail_path
        except Exception as e:
            print(f"   ⚠ Ошибка генерации превью: {e}")
            return None


def main():
    """CLI для генерации видео V2"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Генератор видео V2 из текстового описания")
    parser.add_argument("topic", nargs="?", help="Тема видео")
    parser.add_argument("--language", "-l", default="en", help="Language (en, ru)")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Длительность (сек)")
    parser.add_argument("--style", "-s", help="Стиль видео")
    parser.add_argument("--scenes", "-n", type=int, help="Количество сцен")
    parser.add_argument("--output", "-o", help="Имя выходного файла")
    parser.add_argument("--fireworks-key", help="Fireworks API key")
    parser.add_argument("--whisk-cookie", help="Whisk cookie")
    parser.add_argument("--pexels-key", help="Pexels API key для стоковых фото")
    parser.add_argument("--use-stock", action="store_true", help="Использовать стоковые фото Pexels")
    parser.add_argument("--no-real", action="store_true", help="Не использовать реальные фото")
    parser.add_argument("--fast", action="store_true", help="Быстрый рендер (низкое качество)")
    parser.add_argument("--cpu", action="store_true", help="Использовать CPU вместо GPU")
    
    args = parser.parse_args()
    
    # Запрос темы если не указана
    topic = args.topic
    if not topic:
        topic = input("🎬 Введите тему видео: ").strip()
        if not topic:
            print("❌ Тема не может быть пустой")
            return
    
    # API ключи
    fireworks_key = args.fireworks_key or os.environ.get("FIREWORKS_API_KEY")
    whisk_cookie = args.whisk_cookie or os.environ.get("WHISK_COOKIE")
    pexels_key = args.pexels_key or os.environ.get("PEXELS_API_KEY")
    
    if not fireworks_key:
        print("⚠ Fireworks API key не указан. Используйте --fireworks-key или FIREWORKS_API_KEY")
    
    if not whisk_cookie:
        print("⚠ Whisk cookie не указан. Используйте --whisk-cookie или WHISK_COOKIE")
    
    # Создаём генератор
    generator = VideoGeneratorV2(
        fireworks_api_key=fireworks_key,
        whisk_cookie=whisk_cookie,
        pexels_api_key=pexels_key,
        use_real_photos=not args.no_real,
        use_stock_photos=args.use_stock
    )
    
    # Генерируем видео
    video_path = generator.generate_video(
        topic=topic,
        language=args.language,
        duration=args.duration,
        style=args.style,
        num_scenes=args.scenes,
        video_filename=args.output,
        fast=args.fast,
        use_gpu=not args.cpu
    )
    
    print(f"\n🎉 Видео V2 готово: {video_path}")
    return video_path


if __name__ == "__main__":
    main()

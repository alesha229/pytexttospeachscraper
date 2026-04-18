"""
Генератор видео из сценария
Автоматизирует процесс создания видео:
1. Генерирует сценарий через Fireworks AI
2. Создаёт изображения через Whisk API
3. Генерирует озвучку через InWorld TTS
4. Собирает всё в видео через moviepy

Использование:
    python video_generator.py "Тема видео"
    python video_generator.py "Тема" --duration 60 --scenes 5
    python video_generator.py --topic "Тема" --language en --style cinematic

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
        - scenario.json (сценарий)
        - images/ (изображения сцен)
        - audio/ (аудио озвучки)
        - videos/ (финальное видео)
"""

import os
import sys
import json
import time
from typing import Optional

from video_scenario_planner import VideoScenarioPlanner
from image_generator import ImageGenerator, WhiskAPI, CONFIG as IMAGE_CONFIG
from tts_engine import tts, COOKIES as TTS_COOKIES
from video_assembler import VideoAssembler, VideoScene, create_video_from_scenario

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "video_output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


class VideoGenerator:
    """Генератор видео из текстового описания"""
    
    def __init__(
        self,
        fireworks_api_key: str = None,
        whisk_cookie: str = None,
        inworld_cookies: dict = None
    ):
        """
        Инициализация генератора
        
        Args:
            fireworks_api_key: API ключ для Fireworks AI
            whisk_cookie: Cookie для Whisk API (Google Labs)
            inworld_cookies: Cookies для InWorld TTS
        """
        self.fireworks_api_key = fireworks_api_key
        self.whisk_cookie = whisk_cookie or IMAGE_CONFIG.get("cookie")
        self.inworld_cookies = inworld_cookies
        
        self.scenario_planner = VideoScenarioPlanner(api_key=fireworks_api_key)
        self.image_generator = None # Will be initialized per video
        self.video_assembler = None # Will be initialized per video
    
    def generate_video(
        self,
        topic: str,
        language: str = "ru",
        duration: int = 30,
        style: str = None,
        num_scenes: int = None,
        video_filename: str = None
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
        # Шаг 1: Генерация сценария
        print("\n📝 Шаг 1: Генерация сценария...")
        scenario = self.scenario_planner.create_scenario(
            topic=topic,
            language=language,
            target_duration=duration,
            style=style,
            num_scenes=num_scenes
        )
        
        # Создаем папку для конкретного видео на основе названия сценария
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in scenario.get("title", "video")[:50]).strip()
        video_id = f"{safe_title}_{int(time.time())}"
        video_base_dir = os.path.join(OUTPUT_DIR, video_id)
        
        images_dir = os.path.join(video_base_dir, "images")
        audio_dir = os.path.join(video_base_dir, "audio")
        videos_dir = os.path.join(video_base_dir, "videos")
        
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)
        
        # Инициализируем генераторы с правильными папками
        self.image_generator = ImageGenerator(cookie=self.whisk_cookie, output_dir=images_dir)
        self.video_assembler = VideoAssembler(output_dir=videos_dir)
        
        print("\n" + "="*60)
        print(f"🎬 ГЕНЕРАЦИЯ ВИДЕО: {topic}")
        print(f"📂 Папка проекта: {video_base_dir}")
        print("="*60)
        
        scenario_file = os.path.join(video_base_dir, "scenario.json")
        self.scenario_planner.save_scenario(scenario, scenario_file)
        self.scenario_planner.print_scenario(scenario)
        
        # Шаг 2: Генерация изображений
        print("\n🎨 Шаг 2: Генерация изображений...")
        image_paths = self._generate_images(scenario, images_dir)
        
        # Шаг 3: Генерация аудио
        print("\n🎙️ Шаг 3: Генерация озвучки...")
        audio_paths = self._generate_audio(scenario, audio_dir)
        
        # Шаг 4: Сборка видео
        print("\n🎬 Шаг 4: Сборка видео...")
        video_path = self._assemble_video(scenario, image_paths, audio_paths, videos_dir, video_filename)
        
        print("\n" + "="*60)
        print(f"✅ ВИДЕО ГОТОВО: {video_path}")
        print("="*60 + "\n")
        
        return video_path
    
    def _generate_images(self, scenario: dict, images_dir: str) -> dict:
        """
        Генерирует изображения для всех сцен
        
        Returns:
            Dict {scene_number: image_path}
        """
        image_paths = {}
        scenes = scenario.get("scenes", [])
        
        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i+1)
            prompt = scene.get("image_prompt", "")
            
            if not prompt:
                print(f"⚠ Сцена {scene_num}: нет промпта, пропускаем изображение")
                continue
            
            print(f"   Сцена {scene_num}: {prompt[:50]}...")
            
            try:
                print(f"   ⏳ Генерация изображения для сцены {scene_num}...")
                # Генерируем изображение
                saved_paths = self.image_generator.generate(
                    prompt=prompt,
                    model="IMAGEN_3_5",
                    aspect_ratio=scene.get("image_aspect_ratio", "IMAGE_ASPECT_RATIO_LANDSCAPE"),
                    seed=scene.get("image_seed", 0),
                    count=1
                )
                
                if saved_paths:
                    # Переименовываем файл для соответствия сцене
                    old_path = saved_paths[0]
                    new_path = os.path.join(images_dir, f"scene_{scene_num}.png")
                    if os.path.exists(old_path):
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        os.rename(old_path, new_path)
                    image_paths[scene_num] = new_path
                    print(f"   ✅ Изображение сохранено: {new_path}")
                else:
                    print(f"   ❌ Ошибка генерации изображения для сцены {scene_num}")
                    image_paths[scene_num] = self._create_placeholder_image(scene_num, images_dir)
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                # Создаём заглушку
                image_paths[scene_num] = self._create_placeholder_image(scene_num, images_dir)
            
            # Пауза между запросами
            time.sleep(2)
        
        return image_paths
    
    def _create_placeholder_image(self, scene_num: int, images_dir: str) -> str:
        """Создаёт изображение-заглушку"""
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new("RGB", (1920, 1080), (30, 30, 60))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except:
            font = ImageFont.load_default()
        
        text = f"Scene {scene_num}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x = (1920 - text_w) // 2
        y = (1080 - text_h) // 2
        
        draw.text((x, y), text, fill="white", font=font)
        
        path = os.path.join(images_dir, f"scene_{scene_num}_placeholder.png")
        img.save(path)
        return path
    
    def _generate_audio(self, scenario: dict, audio_dir: str) -> dict:
        """
        Генерирует аудио для всех сцен
        
        Returns:
            Dict {scene_number: audio_path}
        """
        audio_paths = {}
        scenes = scenario.get("scenes", [])
        
        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i+1)
            voiceover = scene.get("voiceover_text", "")
            
            if not voiceover:
                print(f"⚠ Сцена {scene_num}: нет текста озвучки")
                continue
            
            print(f"   Сцена {scene_num}: {voiceover[:50]}...")
            
            # Путь к аудиофайлу
            audio_path = os.path.join(audio_dir, f"scene_{scene_num}.wav")
            
            # Используем русский голос
            voice_id = "Blake"
            
            try:
                print(f"  🎙️ Озвучка сцены {scene_num}...")
                success = tts(
                    text=voiceover,
                    voice_id=voice_id,
                    output_path=audio_path,
                    max_chunk=1000
                )
                
                if success:
                    audio_paths[scene_num] = audio_path
                    print(f"   ✅ Аудио сохранено: {audio_path}")
                else:
                    print(f"   ❌ Ошибка генерации аудио для сцены {scene_num}, создаю тишину")
                    audio_paths[scene_num] = self._create_silence(scene.get("duration_sec", 5), audio_path)
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}, создаю тишину")
                audio_paths[scene_num] = self._create_silence(scene.get("duration_sec", 5), audio_path)
            
            time.sleep(0.5)
        
        return audio_paths
    
    def _create_silence(self, duration: float, output_path: str) -> str:
        """Создаёт тишину заданной длительности"""
        import wave
        import struct
        
        sample_rate = 48000
        num_samples = int(duration * sample_rate)
        
        with wave.open(output_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b'\x00\x00' * num_samples)
        
        return output_path
    
    def _assemble_video(
        self,
        scenario: dict,
        image_paths: dict,
        audio_paths: dict,
        videos_dir: str,
        video_filename: str = None
    ) -> str:
        """Собирает видео из изображений и аудио"""
        scenes = []
        
        for scene_data in scenario.get("scenes", []):
            scene_num = scene_data.get("scene_number", 0)
            
            img_path = image_paths.get(scene_num)
            audio_path = audio_paths.get(scene_num)
            
            if not img_path or not audio_path:
                print(f"⚠ Сцена {scene_num}: отсутствуют файлы, пропускаем")
                continue
            
            scenes.append(VideoScene(
                image_path=img_path,
                audio_path=audio_path,
                voiceover_text=scene_data.get("voiceover_text", ""),
                duration=scene_data.get("duration_sec", 5),
                scene_number=scene_num
            ))
        
        if not video_filename:
            video_filename = "video.mp4"
        
        # Временно меняем output_dir у ассемблера
        self.video_assembler.output_dir = videos_dir
        
        return self.video_assembler.assemble_video(
            scenes,
            output_filename=video_filename,
            fps=24,
            add_text=False
        )


def main():
    """CLI для генерации видео"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Генератор видео из текстового описания")
    parser.add_argument("topic", nargs="?", help="Тема видео")
    parser.add_argument("--language", "-l", default="en", help="Language (en, ru)")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Длительность (сек)")
    parser.add_argument("--style", "-s", help="Стиль видео")
    parser.add_argument("--scenes", "-n", type=int, help="Количество сцен")
    parser.add_argument("--output", "-o", help="Имя выходного файла")
    parser.add_argument("--fireworks-key", help="Fireworks API key")
    parser.add_argument("--whisk-cookie", help="Whisk cookie")
    
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
    
    if not fireworks_key:
        print("⚠ Fireworks API key не указан. Используйте --fireworks-key или FIREWORKS_API_KEY")
    
    if not whisk_cookie:
        print("⚠ Whisk cookie не указан. Используйте --whisk-cookie или WHISK_COOKIE")
    
    # Создаём генератор
    generator = VideoGenerator(
        fireworks_api_key=fireworks_key,
        whisk_cookie=whisk_cookie
    )
    
    # Генерируем видео
    video_path = generator.generate_video(
        topic=topic,
        language=args.language,
        duration=args.duration,
        style=args.style,
        num_scenes=args.scenes,
        video_filename=args.output
    )
    
    print(f"\n🎉 Видео готово: {video_path}")
    return video_path


if __name__ == "__main__":
    main()

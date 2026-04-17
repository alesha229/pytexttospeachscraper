"""
Быстрый видео-ассемблер через ffmpeg (без MoviePy)
Использует прямые вызовы ffmpeg для максимальной скорости
"""

import os
import sys
import subprocess
import tempfile
from typing import List
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
import wave

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("⚠ pydub не установлен. Установите: pip install pydub")


@dataclass
class VideoScene:
    """Данные для одной сцены видео"""
    image_path: str
    audio_path: str
    voiceover_text: str
    duration: float
    scene_number: int
    overlay_path: str = None


class FastVideoAssembler:
    """Сверхбыстрый сборщик видео через ffmpeg"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or "./output_video"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _check_ffmpeg(self):
        """Проверяет наличие ffmpeg"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise FileNotFoundError("ffmpeg не найден или не работает")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg не найден! Установите ffmpeg и добавьте в PATH.\n"
                "Скачать: https://ffmpeg.org/download.html"
            )
    
    def _create_frame_image(self, scene: VideoScene, output_path: str):
        """Создает изображение для сцены с оверлеем"""
        # Загружаем фон
        bg = Image.open(scene.image_path)
        if bg.size != (1920, 1080):
            bg = bg.resize((1920, 1080), Image.Resampling.LANCZOS)
        
        # Добавляем оверлей если есть
        if scene.overlay_path and os.path.exists(scene.overlay_path):
            overlay = Image.open(scene.overlay_path)
            if overlay.size != (1920, 1080):
                overlay = overlay.resize((1920, 1080), Image.Resampling.LANCZOS)
            bg = Image.alpha_composite(bg.convert("RGBA"), overlay.convert("RGBA"))
            bg = bg.convert("RGB")
        
        bg.save(output_path, optimize=True, compress_level=1)
        bg.close()
    
    def _merge_audio(self, scenes: List[VideoScene], output_path: str):
        """Объединяет все аудиофайлы в один"""
        if not HAS_PYDUB:
            raise ImportError("pydub не установлен")
        
        combined = AudioSegment.empty()
        
        for scene in scenes:
            if os.path.exists(scene.audio_path):
                audio = AudioSegment.from_wav(scene.audio_path)
                combined += audio
        
        combined.export(output_path, format="wav", parameters=["-ac", "1", "-ar", "48000"])
        return len(combined) / 1000.0
    
    def assemble_video(
        self,
        scenes: List[VideoScene],
        output_filename: str = "output.mp4",
        fps: int = 24,
        use_gpu: bool = True,
        fast: bool = True
    ) -> str:
        """
        Быстрая сборка видео через ffmpeg loop (без копирования тысяч файлов)
        """
        self._check_ffmpeg()
        
        if not scenes:
            raise ValueError("Список сцен пуст")
        
        output_path = os.path.join(self.output_dir, output_filename)
        temp_dir = tempfile.mkdtemp(prefix="fast_video_")
        
        try:
            print(f"\n🎬 БЫСТРАЯ СБОРКА ВИДЕО (ffmpeg loop)")
            print(f"📊 Сцен: {len(scenes)}, FPS: {fps}")
            print(f"🚀 GPU: {'ON' if use_gpu else 'OFF'}")
            print("="*60)
            
            # Шаг 1: Создаем изображения для сцен
            print("\n📸 Шаг 1: Подготовка изображений...")
            scene_images = []
            
            for i, scene in enumerate(scenes):
                img_path = os.path.join(temp_dir, f"scene_{i}.jpg")
                self._create_scene_image(scene, img_path)
                scene_images.append(img_path)
                print(f"   Сцена {i+1}: {scene.duration:.1f} сек")
            
            # Шаг 2: Объединяем аудио
            print("\n🎵 Шаг 2: Объединение аудио...")
            audio_path = os.path.join(temp_dir, "combined.wav")
            audio_duration = self._merge_audio(scenes, audio_path)
            print(f"   ✅ Аудио: {audio_duration:.1f} сек")
            
            # Шаг 3: Создаем concat файл для склейки сцен
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, 'w', encoding='utf-8') as f:
                for i, scene in enumerate(scenes):
                    # Для каждой сцены создаем отдельное видео
                    scene_video = os.path.join(temp_dir, f"scene_{i}.mp4")
                    
                    if use_gpu:
                        codec = "h264_nvenc"
                        preset = "p1" if fast else "p4"
                    else:
                        codec = "libx264"
                        preset = "ultrafast" if fast else "medium"
                    
                    # Создаем видео из одного изображения
                    cmd_scene = [
                        "ffmpeg",
                        "-loop", "1",
                        "-i", scene_images[i],
                        "-c:v", codec,
                        "-preset", preset,
                        "-pix_fmt", "yuv420p",
                        "-t", str(scene.duration),
                        "-y",
                        scene_video
                    ]
                    
                    print(f"   Создание сцены {i+1}...")
                    result_scene = subprocess.run(cmd_scene, capture_output=True, text=True)
                    if result_scene.returncode != 0:
                        print(f"   ⚠ Ошибка сцены {i+1}: {result_scene.stderr[:200]}")
                    
                    f.write(f"file '{os.path.basename(scene_video)}'\n")
            
            # Шаг 4: Объединяем сцены
            print("\n🎬 Объединение сцен...")
            merged_video = os.path.join(temp_dir, "merged.mp4")
            
            cmd_concat = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-y",
                merged_video
            ]
            
            result_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
            if result_concat.returncode != 0:
                print(f"   ⚠ Ошибка объединения: {result_concat.stderr[:200]}")
            
            # Шаг 5: Добавляем аудио
            print("\n🎵 Добавление аудио...")
            
            cmd = [
                "ffmpeg",
                "-i", merged_video,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                output_path
            ]
            
            print(f"   Команда: ffmpeg -f concat ...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"\n❌ Ошибка ffmpeg:")
                print(f"   {result.stderr[:1000]}")
                raise RuntimeError(f"ffmpeg вернул код {result.returncode}")
            
            print(f"\n✅ Видео создано: {output_path}")
            print(f"   Размер: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
            print("="*60 + "\n")
            
            return output_path
            
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _create_scene_image(self, scene: VideoScene, output_path: str):
        """Создает JPEG изображение для сцены"""
        img = Image.open(scene.image_path)
        if img.size != (1920, 1080):
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        
        # Добавляем оверлей если есть
        if scene.overlay_path and os.path.exists(scene.overlay_path):
            overlay = Image.open(scene.overlay_path)
            if overlay.size != (1920, 1080):
                overlay = overlay.resize((1920, 1080), Image.Resampling.LANCZOS)
            img = Image.alpha_composite(img.convert("RGBA"), overlay.convert("RGBA"))
            img = img.convert("RGB")
        
        # Сохраняем как JPEG (лучше для ffmpeg)
        img.save(output_path, "JPEG", quality=95)
        img.close()


def main():
    """Тест"""
    print("Fast Video Assembler готов!")
    print("Используйте FastVideoAssembler вместо VideoAssembler")


if __name__ == "__main__":
    main()

"""
Модуль для объединения картинок и аудио в видео
Использует moviepy для создания видео из последовательности изображений и аудиофайлов

Использование:
    # Программно:
    from video_assembler import VideoAssembler, VideoScene
    assembler = VideoAssembler(output_dir="./videos")
    scenes = [VideoScene(image_path="img1.png", audio_path="aud1.wav", voiceover_text="Текст", duration=5, scene_number=1)]
    video_path = assembler.assemble_video(scenes, output_filename="output.mp4")

Вход:
    - scenes (List[VideoScene]): Список сцен
        - image_path (str): Путь к изображению
        - audio_path (str): Путь к аудио
        - voiceover_text (str): Текст озвучки для отображения на видео
        - duration (float): Длительность сцены в секундах
        - scene_number (int): Номер сцены
    - output_filename (str): Имя выходного файла (по умолчанию "output_video.mp4")
    - fps (int): Кадров в секунду (по умолчанию 24)
    - add_text (bool): Добавлять ли текст на видео (по умолчанию True)

Выход:
    - MP4 файл в указанной output_dir
"""

import os
import sys
from typing import List, Tuple
from dataclasses import dataclass

try:
    from moviepy import (
        ImageClip,
        AudioFileClip,
        CompositeVideoClip,
        concatenate_videoclips,
        TextClip,
        CompositeAudioClip,
        ColorClip
    )
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy.editor import (
            ImageClip,
            AudioFileClip,
            CompositeVideoClip,
            concatenate_videoclips,
            TextClip,
            CompositeAudioClip
        )
        from moviepy.video.VideoClip import ColorClip
        HAS_MOVIEPY = True
    except ImportError:
        HAS_MOVIEPY = False
        print("⚠ moviepy не установлен. Установите: pip install moviepy")

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠ Pillow не установлен. Установите: pip install Pillow")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_video")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@dataclass
class VideoScene:
    """Данные для одной сцены видео"""
    image_path: str
    audio_path: str
    voiceover_text: str
    duration: float
    scene_number: int
    overlay_path: str = None


class VideoAssembler:
    """Сборщик видео из изображений и аудио"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        if not HAS_MOVIEPY:
            raise ImportError("moviepy не установлен. Установите: pip install moviepy")
        if not HAS_PIL:
            raise ImportError("Pillow не установлен. Установите: pip install Pillow")
    
    def _fast_gpu_assemble(self, scenes: List[VideoScene], output_path: str, fps: int, add_text: bool, fast: bool) -> str:
        """Быстрая сборка видео через ffmpeg + NVENC без MoviePy"""
        import subprocess
        import numpy as np
        from PIL import Image
        import time
        
        print("\n" + "="*60)
        print("🚀 БЫСТРАЯ GPU СБОРКА (NVENC)")
        print("="*60)
        
        start_time = time.time()
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_gpu_frames")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Генерируем кадры напрямую через PIL
        print(f"\n📸 Генерация {len(scenes)} сцен...")
        frame_count = 0
        
        for scene_idx, scene in enumerate(scenes):
            print(f"   Сцена {scene_idx + 1}/{len(scenes)}")
            
            # Загружаем изображение
            img = Image.open(scene.image_path)
            if img.size != (1920, 1080):
                img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            
            # Определяем количество кадров
            duration = scene.duration
            num_frames = int(duration * fps)
            
            # Добавляем оверлей если есть
            if scene.overlay_path and os.path.exists(scene.overlay_path):
                overlay = Image.open(scene.overlay_path)
                if overlay.size != (1920, 1080):
                    overlay = overlay.resize((1920, 1080), Image.Resampling.LANCZOS)
                img = Image.alpha_composite(img.convert("RGBA"), overlay.convert("RGBA"))
                img = img.convert("RGB")
            
            # Сохраняем кадры (статичное изображение)
            for i in range(num_frames):
                frame_path = os.path.join(temp_dir, f"frame_{frame_count:06d}.png")
                img.save(frame_path, optimize=True, compress_level=1)
                frame_count += 1
            
            img.close()
        
        print(f"   ✅ Сгенерировано {frame_count} кадров")
        
        # Собираем аудио
        print(f"\n🎵 Сборка аудио...")
        temp_audio = os.path.join(os.path.dirname(output_path), "temp_combined.wav")
        
        from pydub import AudioSegment
        combined = AudioSegment.empty()
        
        for scene in scenes:
            if os.path.exists(scene.audio_path):
                audio = AudioSegment.from_wav(scene.audio_path)
                combined += audio
        
        combined.export(temp_audio, format="wav")
        print(f"   ✅ Аудио: {len(combined) / 1000:.1f} сек")
        
        # Конвертируем через ffmpeg с NVENC
        nvenc_preset = "p1" if fast else "p4"
        print(f"\n🎬 Конвертация ffmpeg (NVENC {nvenc_preset})...")
        
        cmd = [
            "ffmpeg",
            "-framerate", str(fps),
            "-i", os.path.join(temp_dir, "frame_%06d.png"),
            "-i", temp_audio,
            "-c:v", "h264_nvenc",
            "-preset", nvenc_preset,
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-y",
            output_path
        ]
        
        t1 = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        t2 = time.time()
        
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        
        total_time = t2 - start_time
        
        if result.returncode == 0:
            print(f"\n{'='*60}")
            print(f"✅ ВИДЕО СОЗДАНО (GPU NVENC)")
            print(f"📁 Путь: {output_path}")
            print(f"⏱️ Время: {total_time:.1f} сек")
            print(f"   Генерация кадров: {t1 - start_time:.1f} сек")
            print(f"   Кодирование NVENC: {t2 - t1:.1f} сек")
            print(f"{'='*60}\n")
            return output_path
        else:
            raise Exception(f"FFmpeg error: {result.stderr[:500]}")
    
    def create_scene_clip(self, scene: VideoScene) -> ImageClip:
        """
        Создаёт видео-клип из одной сцены (изображение + аудио)
        Оптимизировано для экономии памяти: статичное изображение без Ken Burns
        """
        from moviepy import ImageClip
        import numpy as np
        from PIL import Image
        
        # Загружаем аудио для определения длительности
        try:
            audio = AudioFileClip(scene.audio_path)
            duration = audio.duration
        except Exception as e:
            print(f"⚠ Ошибка загрузки аудио: {e}, используем duration из сцены")
            duration = scene.duration
            audio = None
        
        # Загружаем и масштабируем изображение один раз через PIL (быстрее и меньше памяти)
        img = Image.open(scene.image_path)
        # Масштабируем до 1920x1080 если нужно
        if img.size != (1920, 1080):
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        
        # Конвертируем в numpy array
        img_array = np.array(img)
        img.close()  # Освобождаем файл
        
        # Создаем клип из массива
        img_clip = ImageClip(img_array).with_duration(duration)
        
        # Добавляем аудио если есть
        if audio:
            img_clip = img_clip.with_audio(audio)
        
        # Добавляем оверлей если есть (без CompositeVideoClip)
        if scene.overlay_path and os.path.exists(scene.overlay_path):
            try:
                overlay_img = Image.open(scene.overlay_path)
                if overlay_img.size != (1920, 1080):
                    overlay_img = overlay_img.resize((1920, 1080), Image.Resampling.LANCZOS)
                
                overlay_array = np.array(overlay_img)
                overlay_img.close()
                
                # Создаем оверлей клип
                overlay_clip = ImageClip(overlay_array).with_duration(duration)
                
                # Композим
                img_clip = CompositeVideoClip([img_clip, overlay_clip])
            except Exception as e:
                print(f"⚠ Ошибка добавления оверлея: {e}")
        
        return img_clip
    
    def add_text_overlay(
        self,
        clip: ImageClip,
        text: str,
        fontsize: int = 40,
        color: str = "white",
        position: str = "bottom",
        bg_color: str = "black",
        bg_opacity: float = 0.7
    ) -> CompositeVideoClip:
        """
        Добавляет текстовый оверлей на клип
        
        Args:
            clip: Видео-клип
            text: Текст для отображения
            fontsize: Размер шрифта
            color: Цвет текста
            position: Позиция (bottom, center, top)
            bg_color: Цвет фона
            bg_opacity: Прозрачность фона
            
        Returns:
            CompositeVideoClip с текстом
        """
        # Определяем позицию
        if position == "bottom":
            y_pos = clip.h - 100
        elif position == "center":
            y_pos = "center"
        elif position == "top":
            y_pos = 50
        else:
            y_pos = "center"
        
        # Создаём текстовый клип через PIL (TextClip в MoviePy 2.x часто глючит)
        txt_clip = self._create_text_image(text, clip.w, fontsize, color, bg_color)
        
        # Позиционируем текст
        txt_clip = txt_clip.with_position(("center", y_pos)).with_duration(clip.duration)
        
        # Добавляем полупрозрачный фон под текст
        bg_clip = self._create_background(clip.w, txt_clip.h + 20, bg_color, bg_opacity)
        bg_clip = bg_clip.with_position(("center", y_pos)).with_duration(clip.duration)
        
        # Композим
        return CompositeVideoClip([clip, bg_clip, txt_clip])
    
    def _create_text_image(
        self,
        text: str,
        width: int,
        fontsize: int,
        color: str,
        bg_color: str
    ) -> ImageClip:
        """Создаёт изображение с текстом через PIL (fallback)"""
        import numpy as np
        
        # Создаём изображение
        img = Image.new("RGBA", (width, fontsize * 3), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Пытаемся загрузить шрифт
        try:
            font = ImageFont.truetype("arial.ttf", fontsize)
        except:
            font = ImageFont.load_default()
        
        # Рисуем текст
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = fontsize
        
        draw.text((x, y), text, fill=color, font=font)
        
        # Конвертируем PIL Image в numpy array для MoviePy 2.x
        img_array = np.array(img.convert("RGB"))
        
        # Конвертируем в Clip
        from moviepy import ImageClip
        return ImageClip(img_array).with_duration(1)
    
    def _create_background(
        self,
        width: int,
        height: int,
        color: str,
        opacity: float
    ) -> ImageClip:
        """Создаёт полупрозрачный прямоугольник для фона текста"""
        import numpy as np
        
        # Конвертируем цвет в RGB
        color_map = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
        }
        rgb = color_map.get(color.lower(), (0, 0, 0))
        
        img = Image.new(
            "RGBA",
            (width, height),
            (*rgb, int(255 * opacity))
        )
        
        # Конвертируем PIL Image в numpy array для MoviePy 2.x
        img_array = np.array(img.convert("RGB"))
        
        return ImageClip(img_array).with_duration(1)
    
    def assemble_video(
        self,
        scenes: List[VideoScene],
        output_filename: str = "output_video.mp4",
        fps: int = 24,
        add_text: bool = True,
        fast: bool = False,
        use_gpu: bool = True
    ) -> str:
        """
        Собирает полное видео из списка сцен
        
        Args:
            scenes: Список сцен
            output_filename: Имя выходного файла
            fps: Кадров в секунду
            add_text: Добавлять ли текст на видео
            fast: Быстрый рендер (низкое качество, ultrafast preset)
            use_gpu: Использовать GPU кодирование (NVENC)
            
        Returns:
            Путь к созданному видео
        """
        if not scenes:
            raise ValueError("Список сцен пуст")
        
        print(f"🎬 Сборка видео из {len(scenes)} сцен...")
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        # БЫСТРЫЙ ПУТЬ: Прямой вызов ffmpeg без MoviePy
        if use_gpu:
            return self._fast_gpu_assemble(scenes, output_path, fps, add_text, fast)
        
        # Обычный путь через MoviePy (медленный)
        # Создаём клипы для каждой сцены
        print("🔗 Создание клипов...")
        clips = []
        for i, scene in enumerate(scenes):
            print(f"   Обработка сцены {i+1}/{len(scenes)}...")
            
            try:
                clip = self.create_scene_clip(scene)
                
                # Добавляем текст если нужно
                if add_text and scene.voiceover_text:
                    clip = self.add_text_overlay(
                        clip,
                        scene.voiceover_text,
                        fontsize=35,
                        position="bottom"
                    )
                
                clips.append(clip)
            except Exception as e:
                print(f"⚠ Ошибка обработки сцены {i+1}: {e}")
                # Создаём чёрный клип-заглушку
                clip = ColorClip(
                    size=(1920, 1080),
                    color=(0, 0, 0)
                ).with_duration(scene.duration)
                clips.append(clip)
        
        if not clips:
            raise ValueError("Не удалось создать ни одного клипа для видео")
        
        # Объединяем все клипы
        print("🔗 Объединение клипов...")
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Настройки для быстрого или качественного рендера
        if fast:
            preset = "ultrafast"
            threads = 4
            print("⚡ Режим быстрого рендера (ultrafast)")
        else:
            preset = "medium"
            threads = 8
        
        # GPU кодирование (NVENC) - обход MoviePy через ffmpeg
        if use_gpu:
            try:
                print("\n" + "="*60)
                print("🚀 НАЧАЛО GPU КОДИРОВАНИЯ NVENC")
                print("="*60)
                import subprocess
                import time
                
                start_time = time.time()
                
                # Шаг 1: Рендерим в несжатый AVI
                temp_avi = os.path.join(os.path.dirname(output_path), "temp_raw.avi")
                
                print(f"\n📹 Шаг 1: Экспорт видео в raw формат...")
                print(f"   Выходной файл: {temp_avi}")
                print(f"   FPS: {fps}")
                print(f"   Codec: rawvideo")
                print(f"   Audio: pcm_s16le")
                
                t1 = time.time()
                final_clip.write_videofile(
                    temp_avi,
                    fps=fps,
                    codec="rawvideo",
                    audio_codec="pcm_s16le",
                    audio_bufsize=10000000,
                    logger="bar",
                    threads=1
                )
                t2 = time.time()
                
                print(f"\n✅ Шаг 1 завершен за {t2-t1:.1f} сек")
                print(f"   Размер файла: {os.path.getsize(temp_avi) / 1024 / 1024:.1f} MB")
                
                # Шаг 2: Конвертируем через ffmpeg с NVENC
                nvenc_preset = "p1" if fast else "p4"
                print(f"\n🔄 Шаг 2: Конвертация через ffmpeg...")
                print(f"   Codec: h264_nvenc")
                print(f"   Preset: {nvenc_preset}")
                print(f"   Audio: aac 192k")
                
                cmd = [
                    "ffmpeg",
                    "-i", temp_avi,
                    "-c:v", "h264_nvenc",
                    "-preset", nvenc_preset,
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-y",
                    output_path
                ]
                
                print(f"   Команда: {' '.join(cmd)}")
                
                t3 = time.time()
                result = subprocess.run(cmd, capture_output=True, text=True)
                t4 = time.time()
                
                print(f"\n📊 Результат ffmpeg:")
                print(f"   Return code: {result.returncode}")
                print(f"   Время: {t4-t3:.1f} сек")
                
                if result.stdout:
                    print(f"   stdout: {result.stdout[:200]}")
                if result.stderr:
                    print(f"   stderr: {result.stderr[:500]}")
                
                # Cleanup
                if os.path.exists(temp_avi):
                    size = os.path.getsize(temp_avi)
                    os.remove(temp_avi)
                    print(f"\n🗑️ Удален временный файл: {size/1024/1024:.1f} MB")
                
                if result.returncode == 0:
                    total_time = t4 - start_time
                    print(f"\n{'='*60}")
                    print(f"✅ ВИДЕО СОЗДАНО (GPU NVENC)")
                    print(f"📁 Путь: {output_path}")
                    print(f"⏱️ Общее время: {total_time:.1f} сек")
                    print(f"   Шаг 1 (raw): {t2-t1:.1f} сек")
                    print(f"   Шаг 2 (nvenc): {t4-t3:.1f} сек")
                    print(f"{'='*60}\n")
                    return output_path
                else:
                    raise Exception(f"FFmpeg вернул код {result.returncode}: {result.stderr[:300]}")
                    
            except Exception as e:
                print(f"\n⚠ GPU КОДИРОВАНИЕ НЕ УДАЛОСЬ!")
                print(f"   Ошибка: {e}")
                print(f"   🔄 Переключаюсь на CPU кодирование...\n")
                # Cleanup при ошибке
                temp_avi = os.path.join(os.path.dirname(output_path), "temp_raw.avi")
                if os.path.exists(temp_avi):
                    os.remove(temp_avi)
        
        # CPU кодирование (fallback) с оптимизацией
        print(f"🔄 Рендеринг на CPU (preset={preset}, threads={threads})...")
        final_clip.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            preset=preset,
            logger="bar",
            threads=threads,
            temp_audiofile="temp_audio.m4a",
            remove_temp=True,
            ffmpeg_params=["-tune", "animation"] if fast else []
        )
        print(f"✅ Видео создано (CPU): {output_path}")
        
        # Освобождаем ресурсы
        final_clip.close()
        for clip in clips:
            clip.close()
        
        return output_path


def create_video_from_scenario(
    scenario: dict,
    images_dir: str,
    audio_dir: str,
    output_filename: str = None
) -> str:
    """
    Создаёт видео из сценария, картинок и аудио
    
    Args:
        scenario: Сценарий из VideoScenarioPlanner
        images_dir: Папка с картинками
        audio_dir: Папка с аудио
        output_filename: Имя выходного файла
        
    Returns:
        Путь к видео
    """
    assembler = VideoAssembler()
    
    scenes = []
    for scene_data in scenario.get("scenes", []):
        scene_num = scene_data.get("scene_number", 0)
        
        # Ищем файлы
        img_pattern = f"scene_{scene_num}"
        audio_pattern = f"scene_{scene_num}"
        
        # Находим конкретные файлы
        img_file = None
        audio_file = None
        
        for f in os.listdir(images_dir):
            if img_pattern in f and f.endswith((".png", ".jpg", ".jpeg")):
                img_file = os.path.join(images_dir, f)
                break
        
        for f in os.listdir(audio_dir):
            if audio_pattern in f and f.endswith(".wav"):
                audio_file = os.path.join(audio_dir, f)
                break
        
        if img_file and audio_file:
            scenes.append(VideoScene(
                image_path=img_file,
                audio_path=audio_file,
                voiceover_text=scene_data.get("voiceover_text", ""),
                duration=scene_data.get("duration_sec", 5),
                scene_number=scene_num
            ))
    
    if not output_filename:
        output_filename = f"video_{scenario.get('title', 'output')[:30].replace(' ', '_')}.mp4"
    
    return assembler.assemble_video(scenes, output_filename)


if __name__ == "__main__":
    # Тестовый пример
    print("Video Assembler модуль загружен")
    print("Используйте create_video_from_scenario() для создания видео")

import os
import sys
import subprocess
import tempfile
from typing import List
from dataclasses import dataclass
from PIL import Image
import wave

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("Warning: pydub not installed. Install: pip install pydub")


@dataclass
class VideoScene:
    image_path: str
    audio_path: str
    voiceover_text: str
    duration: float
    scene_number: int
    overlay_path: str = None


class FastVideoAssembler:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or "./output_video"
        os.makedirs(self.output_dir, exist_ok=True)

    def _check_ffmpeg(self):
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise FileNotFoundError("ffmpeg not found or not working")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found! Install ffmpeg and add to PATH.\n"
                "Download: https://ffmpeg.org/download.html"
            )

    def _create_scene_image(self, scene: VideoScene, output_path: str):
        img = Image.open(scene.image_path)
        if img.size != (1920, 1080):
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        if scene.overlay_path and os.path.exists(scene.overlay_path):
            overlay = Image.open(scene.overlay_path)
            if overlay.size != (1920, 1080):
                overlay = overlay.resize((1920, 1080), Image.Resampling.LANCZOS)
            img = Image.alpha_composite(img.convert("RGBA"), overlay.convert("RGBA"))
            img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=95)
        img.close()

    def _merge_audio(self, scenes: List[VideoScene], output_path: str):
        if not HAS_PYDUB:
            raise ImportError("pydub not installed")
        combined = AudioSegment.empty()
        for scene in scenes:
            if os.path.exists(scene.audio_path):
                audio = AudioSegment.from_wav(scene.audio_path)
                combined += audio
        combined.export(output_path, format="wav", parameters=["-ac", "1", "-ar", "48000"])
        return len(combined) / 1000.0

    def assemble_video(self, scenes: List[VideoScene], output_filename: str = "output.mp4",
                       fps: int = 24, use_gpu: bool = True, fast: bool = True) -> str:
        self._check_ffmpeg()
        if not scenes:
            raise ValueError("Scene list is empty")

        output_path = os.path.join(self.output_dir, output_filename)
        temp_dir = tempfile.mkdtemp(prefix="fast_video_")

        try:
            print(f"\nFAST VIDEO ASSEMBLY (ffmpeg loop)")
            print(f"Scenes: {len(scenes)}, FPS: {fps}, GPU: {'ON' if use_gpu else 'OFF'}")
            print("=" * 60)

            print("\nStep 1: Preparing images...")
            scene_images = []
            for i, scene in enumerate(scenes):
                img_path = os.path.join(temp_dir, f"scene_{i}.jpg")
                self._create_scene_image(scene, img_path)
                scene_images.append(img_path)
                print(f"  Scene {i + 1}: {scene.duration:.1f}s")

            print("\nStep 2: Merging audio...")
            audio_path = os.path.join(temp_dir, "combined.wav")
            audio_duration = self._merge_audio(scenes, audio_path)
            print(f"  Audio: {audio_duration:.1f}s")

            print("\nStep 3: Creating scene videos...")
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, 'w', encoding='utf-8') as f:
                for i, scene in enumerate(scenes):
                    scene_video = os.path.join(temp_dir, f"scene_{i}.mp4")
                    if use_gpu:
                        codec = "h264_nvenc"
                        preset = "p1" if fast else "p4"
                    else:
                        codec = "libx264"
                        preset = "ultrafast" if fast else "medium"

                    cmd_scene = [
                        "ffmpeg", "-loop", "1", "-i", scene_images[i],
                        "-c:v", codec, "-preset", preset,
                        "-pix_fmt", "yuv420p", "-t", str(scene.duration),
                        "-y", scene_video
                    ]
                    print(f"  Creating scene {i + 1}...")
                    result_scene = subprocess.run(cmd_scene, capture_output=True, text=True)
                    if result_scene.returncode != 0:
                        print(f"  Warning scene {i + 1}: {result_scene.stderr[:200]}")
                    f.write(f"file '{os.path.basename(scene_video)}'\n")

            print("\nStep 4: Concatenating scenes...")
            merged_video = os.path.join(temp_dir, "merged.mp4")
            cmd_concat = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file,
                          "-c", "copy", "-y", merged_video]
            result_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
            if result_concat.returncode != 0:
                print(f"  Concat error: {result_concat.stderr[:200]}")

            print("\nStep 5: Adding audio...")
            cmd = ["ffmpeg", "-i", merged_video, "-i", audio_path,
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                   "-shortest", "-y", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ffmpeg error: {result.stderr[:1000]}")
                raise RuntimeError(f"ffmpeg returned code {result.returncode}")

            print(f"\nVideo created: {output_path}")
            print(f"  Size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
            print("=" * 60 + "\n")
            return output_path

        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

import os
import re
import time
import wave
from typing import Optional, Dict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

from .scenario import VideoScenarioPlannerV2
from .tts import tts, create_silence
from .assembler import FastVideoAssembler, VideoScene
from .ae_project import AEJsonGenerator
from ..images.pipeline import ImagePipeline
from ..images.whisk import ImageGenerator
from ..images.thumbnail import ThumbnailGenerator
from ..config import VIDEO_OUTPUT_DIR, WHISK_COOKIE, TTS_DEFAULT_VOICE_ID, HORROR_STYLE_PROMPT


class VideoGeneratorV2:
    def __init__(
        self,
        fireworks_api_key: str = None,
        whisk_cookie: str = None,
        pexels_api_key: str = None,
        voice_id: str = None,
        use_real_photos: bool = True,
        use_stock_photos: bool = False,
        validate_images: bool = True,
        enable_upscale: bool = True,
        video_theme: str = None,
    ):
        self.fireworks_api_key = fireworks_api_key
        self.whisk_cookie = whisk_cookie or WHISK_COOKIE
        self.voice_id = voice_id or TTS_DEFAULT_VOICE_ID
        self.use_real_photos = use_real_photos
        self.use_stock_photos = use_stock_photos
        self.validate_images = validate_images
        self.enable_upscale = enable_upscale
        self.video_theme = video_theme or HORROR_STYLE_PROMPT

        self.scenario_planner = VideoScenarioPlannerV2(api_key=fireworks_api_key)
        self.image_generator = None
        self.fast_assembler = None
        self.thumbnail_generator = None

        if self.whisk_cookie:
            self.thumbnail_generator = ThumbnailGenerator(
                whisk_cookie=self.whisk_cookie,
                output_dir=str(VIDEO_OUTPUT_DIR / "thumbnails")
            )

        self.pipeline = ImagePipeline(
            video_theme=self.video_theme,
            validate_images=validate_images,
            whisk_cookie=whisk_cookie,
            fireworks_api_key=fireworks_api_key,
            pexels_api_key=pexels_api_key,
            enable_upscale=enable_upscale,
        )

    def generate_video(
        self,
        topic: str,
        language: str = "ru",
        duration: int = 30,
        style: str = None,
        num_scenes: int = None,
        video_filename: str = None,
        fast: bool = False,
        use_gpu: bool = True,
        generate_ae: bool = True,
        context: str = None,
    ) -> str:
        print("\nStep 1: Generating scenario...")
        scenario = self.scenario_planner.create_scenario(
            topic=topic, language=language, target_duration=duration,
            style=style, num_scenes=num_scenes, context=context
        )

        self._set_video_theme(scenario)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic[:50]).strip()
        video_id = f"{safe_title}_{int(time.time())}"
        video_base_dir = os.path.join(str(VIDEO_OUTPUT_DIR), video_id)

        assets_dir = os.path.join(video_base_dir, "assets")
        audio_dir = os.path.join(video_base_dir, "audio")
        overlays_dir = os.path.join(video_base_dir, "overlays")
        videos_dir = os.path.join(video_base_dir, "videos")

        for d in [assets_dir, audio_dir, overlays_dir, videos_dir]:
            os.makedirs(d, exist_ok=True)

        self.image_generator = ImageGenerator(cookie=self.whisk_cookie, output_dir=assets_dir)
        self.fast_assembler = FastVideoAssembler(output_dir=videos_dir)

        print("\n" + "=" * 60)
        print(f"VIDEO GENERATION V2: {topic}")
        print(f"Project dir: {video_base_dir}")
        print("=" * 60)

        scenario_file = os.path.join(video_base_dir, "scenario.json")
        self.scenario_planner.save_scenario(scenario, scenario_file)
        self.scenario_planner.print_scenario(scenario)

        print("\nStep 2: Processing assets...")
        assets_map = self._process_assets_manifest(scenario, assets_dir)

        audio_future = None
        with ThreadPoolExecutor(max_workers=2) as pool:
            print("\nStarting audio generation in background...")
            audio_future = pool.submit(self._generate_audio, scenario, audio_dir)

            print("\nStep 3: Generating and upscaling background images...")
            background_paths = self._generate_and_upscale_backgrounds(scenario, assets_dir, assets_map)

        print("\nWaiting for audio...")
        audio_paths = audio_future.result() if audio_future else {}

        print("\nStep 4: Creating overlays...")
        overlay_paths = self._create_overlays(scenario, overlays_dir)

        print("\nStep 6: Assembling video...")
        video_path = self._assemble_video(
            scenario, background_paths, audio_paths, overlay_paths,
            videos_dir, video_filename, fast=fast, use_gpu=use_gpu
        )

        if generate_ae:
            print("\nStep 7: Generating AE project...")
            ae_gen = AEJsonGenerator()
            try:
                ae_json_path = ae_gen.generate(
                    scenario=scenario,
                    assets_dir=assets_dir,
                    audio_dir=audio_dir,
                    output_dir=video_base_dir,
                )
                print(f"AE project: {ae_json_path}")
            except Exception as e:
                print(f"AE project error: {e}")

        print("\nStep 8: Generating thumbnail...")
        thumbnail_path = self._generate_thumbnail(topic, video_base_dir)

        self.pipeline.cleanup()

        print("\n" + "=" * 60)
        print(f"VIDEO V2 READY: {video_path}")
        if thumbnail_path:
            print(f"THUMBNAIL READY: {thumbnail_path}")
        print("=" * 60 + "\n")

        return video_path

    def generate_assets_only(
        self,
        topic: str,
        language: str = "ru",
        duration: int = 30,
        style: str = None,
        num_scenes: int = None,
        context: str = None,
    ) -> str:
        print("\nStep 1: Generating scenario...")
        scenario = self.scenario_planner.create_scenario(
            topic=topic, language=language, target_duration=duration,
            style=style, num_scenes=num_scenes, context=context
        )

        self._set_video_theme(scenario)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic[:50]).strip()
        video_id = f"{safe_title}_{int(time.time())}"
        video_base_dir = os.path.join(str(VIDEO_OUTPUT_DIR), video_id)

        assets_dir = os.path.join(video_base_dir, "assets")
        audio_dir = os.path.join(video_base_dir, "audio")
        overlays_dir = os.path.join(video_base_dir, "overlays")
        thumbnail_dir = os.path.join(video_base_dir, "thumbnail")

        for d in [assets_dir, audio_dir, overlays_dir, thumbnail_dir]:
            os.makedirs(d, exist_ok=True)

        if self.whisk_cookie:
            self.image_generator = ImageGenerator(cookie=self.whisk_cookie, output_dir=assets_dir)

        print("\n" + "=" * 60)
        print(f"ASSETS GENERATION V2: {topic}")
        print(f"Project dir: {video_base_dir}")
        print("=" * 60)

        scenario_file = os.path.join(video_base_dir, "scenario.json")
        self.scenario_planner.save_scenario(scenario, scenario_file)
        self.scenario_planner.print_scenario(scenario)

        print("\nStep 2: Processing assets...")
        assets_map = self._process_assets_manifest(scenario, assets_dir)

        print("\nStep 3: Generating backgrounds...")
        background_paths = self._generate_backgrounds(scenario, assets_dir, assets_map)

        print("\nStep 4: Generating audio...")
        audio_paths = self._generate_audio(scenario, audio_dir)

        print("\nStep 5: Creating overlays...")
        overlay_paths = self._create_overlays(scenario, overlays_dir)

        print("\nStep 6: Generating AE project...")
        ae_gen = AEJsonGenerator()
        try:
            ae_json_path = ae_gen.generate(
                scenario=scenario, assets_dir=assets_dir,
                audio_dir=audio_dir, output_dir=video_base_dir,
            )
            print(f"AE project: {ae_json_path}")
        except Exception as e:
            print(f"AE project error: {e}")

        print("\nStep 7: Generating thumbnail...")
        self._generate_thumbnail(topic, video_base_dir)

        self.pipeline.cleanup()

        print("\n" + "=" * 60)
        print(f"ASSETS V2 READY")
        print(f"Project dir: {video_base_dir}")
        print("=" * 60 + "\n")

        return video_base_dir

    def _set_video_theme(self, scenario: dict):
        metadata = scenario.get("metadata", {})
        vibe = metadata.get("vibe", "")
        theme = self.video_theme
        if vibe and len(vibe) > len(theme):
            theme = vibe
        self.video_theme = theme
        self.pipeline.set_theme(theme)

    def _process_assets_manifest(self, scenario: dict, assets_dir: str) -> dict:
        assets_map = {}
        manifest = scenario.get("assets_manifest", [])
        if not manifest:
            return assets_map

        print(f"   Found {len(manifest)} assets to process")

        for asset in manifest:
            if isinstance(asset, str):
                asset = {"type": "object", "name": asset, "description": "", "search_query": ""}
            asset_type = asset.get("type", "object")
            asset_name = asset.get("name", "")
            asset_desc = asset.get("description", "")
            search_query = asset.get("search_query", "")
            if not asset_name:
                continue

            print(f"   Processing: {asset_name} ({asset_type})")

            image_path = None
            block_idx = abs(hash(asset_name)) % 10000

            if asset_type == "person":
                image_path = self.pipeline.get_person_image(
                    name=search_query or asset_name,
                    desc=asset_desc,
                    assets_dir=assets_dir,
                    filename_prefix=f"person_{self._safe_asset_filename(search_query or asset_name)}",
                    block_index=block_idx,
                )
            else:
                query = search_query or asset_desc or asset_name
                orientation = "landscape" if asset_type == "location" else "landscape"
                image_path = self.pipeline.get_image(
                    query=query,
                    image_type=asset_type,
                    orientation=orientation,
                    assets_dir=assets_dir,
                    block_index=block_idx,
                )

            if image_path:
                assets_map[asset_name] = image_path
            elif asset_type == "person":
                assets_map[asset_name] = self._create_person_placeholder(asset_name, asset_desc, assets_dir)
            else:
                clean_prompt = self._clean_prompt_for_whisk(asset_name, asset_desc, asset_type)
                generated = self.pipeline.generate_image(
                    prompt=clean_prompt, block_index=block_idx,
                    assets_dir=assets_dir, asset_type=asset_type,
                )
                if generated:
                    assets_map[asset_name] = generated
                else:
                    assets_map[asset_name] = self._create_placeholder_image(block_idx, assets_dir)

        return assets_map

    @staticmethod
    def _safe_asset_filename(name: str) -> str:
        safe = re.sub(r'[^a-zA-Z0-9_\s]', '', name)
        safe = re.sub(r'\s+', ' ', safe).strip()
        if not safe:
            safe = f"asset_{abs(hash(name)) % 10000}"
        return safe.replace(' ', '_')

    @staticmethod
    def _clean_prompt_for_whisk(name: str, description: str, asset_type: str) -> str:
        name_lower = name.lower()
        for prefix in ["generated_image:", "stock_video:", "stock_photo:", "person_photo:"]:
            if name_lower.startswith(prefix):
                name = name[len(prefix):].strip()
                name_lower = name.lower()

        prominent_names = ["victor surge", "eric knudsen", "slenderman", "slender man",
                           "jeff the killer", "sonic.exe", "herobrine"]
        is_prominent = any(pn in name_lower for pn in prominent_names)

        if asset_type == "person" and is_prominent:
            return "An anonymous artist working at computer in dark room, mysterious figure"
        if asset_type == "person":
            return f"A person portrait: {description}" if description else "A person portrait"
        if asset_type == "character":
            return "A tall faceless figure in black suit standing in dark forest, mysterious silhouette, horror style, photorealistic"

        clean_name = re.sub(r'\([^)]*\)', '', name).strip()
        clean_desc = re.sub(r'\([^)]*\)', '', description).strip()
        if any(pn in clean_desc.lower() for pn in prominent_names):
            clean_desc = "mysterious dark figure, faceless silhouette, horror atmosphere"

        if not clean_name:
            return f"{asset_type}: {clean_desc}" if clean_desc else f"{asset_type}"
        return f"{asset_type}: {clean_name}. {clean_desc}"

    def _create_person_placeholder(self, name: str, description: str, assets_dir: str) -> str:
        img = Image.new("RGB", (1920, 1080), (40, 40, 60))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 60)
            font_small = ImageFont.truetype("arial.ttf", 40)
        except Exception:
            font = ImageFont.load_default()
            font_small = font
        center_x, center_y = 960, 400
        radius = 150
        draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], fill=(80, 80, 100))
        bbox = draw.textbbox((0, 0), name, font=font)
        draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 600), name, fill="white", font=font)
        if description:
            bbox = draw.textbbox((0, 0), description, font=font_small)
            draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 680), description, fill=(200, 200, 200), font=font_small)
        path = os.path.join(assets_dir, f"person_{name.replace(' ', '_')}_placeholder.png")
        img.save(path)
        return path

    def _generate_and_upscale_backgrounds(self, scenario: dict, assets_dir: str, assets_map: dict) -> dict:
        background_paths = {}
        timeline = scenario.get("timeline", [])
        total_bg = len(timeline)

        for i, block in enumerate(timeline):
            bg = block.get("background", {})
            bg_type = bg.get("type", "generated_image")
            bg_prompt = bg.get("prompt", "")

            if not bg_prompt:
                background_paths[i] = self._create_placeholder_image(i, assets_dir)
                continue

            if total_bg > 20:
                print(f"   Background [{i + 1}/{total_bg}]: {bg_type} - {bg_prompt[:40]}...")
            else:
                print(f"   Block {i + 1}: {bg_type} - {bg_prompt[:50]}...")
            try:
                image_path = None
                bg_target = f"background_{i + 1}.png"

                if bg_type == "person_photo":
                    person_name = bg_prompt.split(":")[0] if ":" in bg_prompt else bg_prompt
                    print(f"   Searching for person photo: {person_name}")
                    if person_name in assets_map:
                        image_path = assets_map[person_name]
                        image_path = self.pipeline._check_and_refine_style(
                            image_path, bg_prompt, assets_dir, i + 1,
                            target_name=bg_target,
                        )
                    else:
                        image_path = self.pipeline.get_person_image(
                            name=person_name, desc=bg_prompt,
                            assets_dir=assets_dir,
                            filename_prefix=f"bg_person_{i + 1}",
                            block_index=i + 1,
                        )
                    if not image_path:
                        image_path = self._create_person_placeholder(person_name, bg_prompt, assets_dir)

                elif bg_type == "stock_photo":
                    image_path = self.pipeline.get_image(
                        query=bg_prompt, image_type="stock",
                        orientation="landscape", assets_dir=assets_dir,
                        block_index=i + 1,
                    )

                if not image_path:
                    clean_bg_prompt = self._clean_prompt_for_whisk(
                        bg_prompt.split(":")[0] if ":" in bg_prompt else "", bg_prompt, bg_type
                    )
                    image_path = self.pipeline.generate_image(
                        prompt=clean_bg_prompt, block_index=i + 1,
                        assets_dir=assets_dir, asset_type=bg_type,
                        target_name=bg_target,
                    )

                if not image_path:
                    image_path = self._create_placeholder_image(i, assets_dir)

                if self.enable_upscale:
                    print(f"   Starting upscale for background {i + 1}...")
                    try:
                        image_path = self.pipeline.upscale_image(image_path, assets_dir, i + 1,
                                                                  target_name=bg_target)
                        print(f"   Upscaled: {os.path.basename(image_path)}")
                    except Exception as e:
                        print(f"   Upscale failed: {e}")

                background_paths[i] = image_path
            except Exception as e:
                print(f"   Error: {e}")
                background_paths[i] = self._create_placeholder_image(i, assets_dir)

            time.sleep(1 if total_bg > 30 else 2)

        return background_paths

    def _generate_backgrounds(self, scenario: dict, assets_dir: str, assets_map: dict) -> dict:
        background_paths = {}
        timeline = scenario.get("timeline", [])
        for i, block in enumerate(timeline):
            bg = block.get("background", {})
            bg_type = bg.get("type", "generated_image")
            bg_prompt = bg.get("prompt", "")

            if not bg_prompt:
                background_paths[i] = self._create_placeholder_image(i, assets_dir)
                continue

            print(f"   Block {i + 1}: {bg_type} - {bg_prompt[:50]}...")
            try:
                image_path = None
                bg_target = f"background_{i + 1}.png"

                if bg_type == "person_photo":
                    person_name = bg_prompt.split(":")[0] if ":" in bg_prompt else bg_prompt
                    if person_name in assets_map:
                        image_path = assets_map[person_name]
                        image_path = self.pipeline._check_and_refine_style(
                            image_path, bg_prompt, assets_dir, i + 1,
                            target_name=bg_target,
                        )
                    else:
                        image_path = self.pipeline.get_person_image(
                            name=person_name, desc=bg_prompt,
                            assets_dir=assets_dir,
                            filename_prefix=f"bg_person_{i + 1}",
                            block_index=i + 1,
                        )
                    if not image_path:
                        image_path = self._create_person_placeholder(person_name, bg_prompt, assets_dir)

                elif bg_type == "stock_photo":
                    image_path = self.pipeline.get_image(
                        query=bg_prompt, image_type="stock",
                        orientation="landscape", assets_dir=assets_dir,
                        block_index=i + 1,
                    )

                if not image_path:
                    clean_bg_prompt = self._clean_prompt_for_whisk(
                        bg_prompt.split(":")[0] if ":" in bg_prompt else "", bg_prompt, bg_type
                    )
                    image_path = self.pipeline.generate_image(
                        prompt=clean_bg_prompt, block_index=i + 1,
                        assets_dir=assets_dir, asset_type=bg_type,
                        target_name=bg_target,
                    )

                if not image_path:
                    image_path = self._create_placeholder_image(i, assets_dir)

                background_paths[i] = image_path
            except Exception as e:
                print(f"   Error: {e}")
                background_paths[i] = self._create_placeholder_image(i, assets_dir)

            time.sleep(2)
        return background_paths

    def _create_placeholder_image(self, block_index: int, assets_dir: str) -> str:
        img = Image.new("RGB", (1920, 1080), (30, 30, 60))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except Exception:
            font = ImageFont.load_default()
        text = f"Block {block_index + 1}"
        bbox = draw.textbbox((0, 0), text, font=font)
        draw.text(((1920 - (bbox[2] - bbox[0])) // 2, (1080 - (bbox[3] - bbox[1])) // 2),
                  text, fill="white", font=font)
        path = os.path.join(assets_dir, f"background_{block_index + 1}_placeholder.png")
        img.save(path)
        return path

    def _generate_audio(self, scenario: dict, audio_dir: str) -> dict:
        audio_paths = {}
        timeline = scenario.get("timeline", [])
        total = len(timeline)
        for i, block in enumerate(timeline):
            voiceover = block.get("voiceover", "")
            if not voiceover:
                continue
            if total > 20:
                print(f"   Audio [{i + 1}/{total}]: {voiceover[:50]}...")
            audio_path = os.path.join(audio_dir, f"block_{i + 1}.wav")
            voice_id = self.voice_id
            try:
                success = tts(text=voiceover, voice_id=voice_id, output_path=audio_path, max_chunk=1000)
                if success:
                    audio_paths[i] = audio_path
                else:
                    audio_paths[i] = create_silence(5, audio_path)
            except Exception:
                audio_paths[i] = create_silence(5, audio_path)
            time.sleep(0.3 if total > 30 else 0.5)
        return audio_paths

    def _create_overlays(self, scenario: dict, overlays_dir: str) -> dict:
        overlay_paths = {}
        timeline = scenario.get("timeline", [])
        for i, block in enumerate(timeline):
            overlays = block.get("overlays", [])
            if not overlays:
                continue
            overlay_path = os.path.join(overlays_dir, f"block_{i + 1}_overlays.png")
            try:
                self._render_overlays(overlays, overlay_path)
                overlay_paths[i] = overlay_path
            except Exception as e:
                print(f"   Overlay error: {e}")
        return overlay_paths

    def _render_overlays(self, overlays: list, output_path: str):
        width, height = 1920, 300
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font_thesis = ImageFont.truetype("arial.ttf", 50)
            font_quote = ImageFont.truetype("arial.ttf", 40)
            font_nameplate = ImageFont.truetype("arial.ttf", 45)
        except Exception:
            font_thesis = ImageFont.load_default()
            font_quote = font_thesis
            font_nameplate = font_thesis

        y_offset = 20
        for overlay in overlays:
            overlay_type = overlay.get("type", "thesis")
            text = overlay.get("text", "") or overlay.get("content", "")
            if not text:
                continue
            if overlay_type == "thesis":
                bbox = draw.textbbox((0, 0), text, font=font_thesis)
                x = (width - (bbox[2] - bbox[0])) // 2
                padding = 20
                draw.rounded_rectangle(
                    [x - padding, y_offset - padding, x + (bbox[2] - bbox[0]) + padding, y_offset + (bbox[3] - bbox[1]) + padding],
                    radius=15, fill=(0, 0, 0, 180))
                draw.text((x, y_offset), text, fill="white", font=font_thesis)
                y_offset += (bbox[3] - bbox[1]) + padding * 2 + 10
            elif overlay_type == "quote":
                quote_text = f'"{text}"'
                bbox = draw.textbbox((0, 0), quote_text, font=font_quote)
                x = (width - (bbox[2] - bbox[0])) // 2
                padding = 15
                draw.rounded_rectangle(
                    [x - padding, y_offset - padding, x + (bbox[2] - bbox[0]) + padding, y_offset + (bbox[3] - bbox[1]) + padding],
                    radius=10, fill=(255, 255, 200, 150))
                draw.text((x, y_offset), quote_text, fill=(50, 50, 50), font=font_quote)
                y_offset += (bbox[3] - bbox[1]) + padding * 2 + 10
            elif overlay_type == "nameplate":
                bbox = draw.textbbox((0, 0), text, font=font_nameplate)
                x = (width - (bbox[2] - bbox[0])) // 2
                padding = 15
                draw.rounded_rectangle(
                    [x - padding, y_offset - padding, x + (bbox[2] - bbox[0]) + padding, y_offset + (bbox[3] - bbox[1]) + padding],
                    radius=10, fill=(100, 100, 200, 200))
                draw.text((x, y_offset), text, fill="white", font=font_nameplate)
                y_offset += (bbox[3] - bbox[1]) + padding * 2 + 10
        img.save(output_path, "PNG")

    def _assemble_video(self, scenario: dict, background_paths: dict, audio_paths: dict,
                         overlay_paths: dict, videos_dir: str, video_filename: str = None,
                         fast: bool = False, use_gpu: bool = True) -> str:
        scenes = []
        timeline = scenario.get("timeline", [])
        for i, block in enumerate(timeline):
            bg_path = background_paths.get(i)
            audio_path = audio_paths.get(i)
            if not bg_path or not audio_path:
                continue
            try:
                with wave.open(audio_path, 'rb') as wf:
                    duration = wf.getnframes() / wf.getframerate()
            except Exception:
                duration = 5
            scenes.append(VideoScene(
                image_path=bg_path, audio_path=audio_path,
                voiceover_text=block.get("voiceover", ""),
                duration=duration, scene_number=i + 1,
                overlay_path=overlay_paths.get(i)
            ))
        if not video_filename:
            video_filename = "video_v2.mp4"
        return self.fast_assembler.assemble_video(
            scenes, output_filename=video_filename, fps=24,
            use_gpu=use_gpu, fast=fast
        )

    def _generate_thumbnail(self, topic: str, video_base_dir: str) -> str:
        if not self.thumbnail_generator:
            return None
        try:
            thumbnail_dir = os.path.join(video_base_dir, "thumbnail")
            os.makedirs(thumbnail_dir, exist_ok=True)
            original_dir = self.thumbnail_generator.output_dir
            self.thumbnail_generator.output_dir = thumbnail_dir
            thumbnail_path = self.thumbnail_generator.generate_thumbnail(topic=topic)
            self.thumbnail_generator.output_dir = original_dir
            return thumbnail_path
        except Exception as e:
            print(f"   Thumbnail error: {e}")
            return None

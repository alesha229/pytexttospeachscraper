import os
import time
from typing import Optional, Dict, List
from pathlib import Path

from .search import ImageSearch
from .validator import ImageValidator
from .whisk import ImageGenerator
from .upscaler import UpscaleManager
from ..config import (
    FIREWORKS_API_KEY, WHISK_COOKIE, PEXELS_API_KEY,
    EXA_API_KEY, TAVILY_API_KEY,
    VALIDATOR_CONFIDENCE_THRESHOLD, STYLE_CONFIDENCE_THRESHOLD,
    HORROR_STYLE_PROMPT,
    UPSCALER_SD_CHECKPOINT, UPSCALER_SD_PROMPT, UPSCALER_SD_NEGATIVE,
    UPSCALER_SD_STRENGTH, UPSCALER_SD_STEPS, UPSCALER_SD_GUIDANCE,
    UPSCALER_SD_SAMPLER, UPSCALER_SD_VAE,
)


class ImagePipeline:
    def __init__(
        self,
        video_theme: str = "",
        validate_images: bool = True,
        whisk_cookie: str = None,
        fireworks_api_key: str = None,
        pexels_api_key: str = None,
        exa_api_key: str = None,
        tavily_api_key: str = None,
        enable_upscale: bool = True,
    ):
        self.video_theme = video_theme
        self.validate_images = validate_images
        self.enable_upscale = enable_upscale

        fw_key = fireworks_api_key or FIREWORKS_API_KEY

        self.validator = None
        if validate_images and fw_key:
            self.validator = ImageValidator(
                api_key=fw_key,
                confidence_threshold=VALIDATOR_CONFIDENCE_THRESHOLD,
                style_confidence_threshold=STYLE_CONFIDENCE_THRESHOLD,
            )
            if video_theme:
                self.validator.video_theme = video_theme

        cookie = whisk_cookie or WHISK_COOKIE
        self.whisk_generator = ImageGenerator(cookie=cookie, output_dir="") if cookie else None

        self.image_search = ImageSearch(
            pexels_key=pexels_api_key or PEXELS_API_KEY,
            validator=self.validator,
            exa_key=exa_api_key or EXA_API_KEY,
            tavily_key=tavily_api_key or TAVILY_API_KEY,
        )

        self.upscaler_manager = None
        if enable_upscale:
            try:
                self.upscaler_manager = UpscaleManager.get_instance()
            except Exception as e:
                print(f"   [pipeline] upscaler init failed: {e}")

    def set_theme(self, video_theme: str):
        self.video_theme = video_theme
        if self.validator:
            self.validator.video_theme = video_theme
        print(f"   [pipeline] theme set: {video_theme}")

    def get_image(self, query: str, image_type: str = "object",
                  orientation: str = "landscape", assets_dir: str = "",
                  block_index: int = 0) -> Optional[str]:
        image_path = self._search_and_download(query, image_type, orientation, assets_dir, block_index)
        if image_path:
            image_path = self._check_and_refine_style(image_path, query, assets_dir, block_index)
        return image_path

    def get_person_image(self, name: str, desc: str = "",
                         assets_dir: str = "", filename_prefix: str = "person",
                         block_index: int = 0) -> Optional[str]:
        queries = [desc or name, name, f"{name} portrait", f"{name} photo"]
        seen = set(q.lower() for q in queries)
        parts = name.strip().split()
        if len(parts) >= 2:
            for q in [f"{parts[0]} {parts[-1]}", f"{parts[-1]} {parts[0]}"]:
                if q.lower() not in seen:
                    queries.append(q)
                    seen.add(q.lower())

        for qi, search_query in enumerate(queries):
            if not search_query:
                continue
            print(f"   [pipeline] person attempt {qi + 1}/{len(queries)}: '{search_query}'")
            image_path = self._search_and_download(search_query, "person", "portrait", assets_dir)
            if image_path:
                image_path = self._check_and_refine_style(image_path, search_query, assets_dir, block_index)
                if image_path:
                    return image_path

        print(f"   [pipeline] person not found: {name}")
        return None

    def _search_and_download(self, query: str, image_type: str,
                              orientation: str, assets_dir: str,
                              block_index: int = 0) -> Optional[str]:
        source_order = []
        if image_type == "person" or image_type == "object":
            source_order = ["real", "exa", "tavily"]
        else:
            source_order = ["real", "exa", "tavily"]

        if self.image_search.services.get("pexels"):
            source_order.append("pexels")

        for source in source_order:
            try:
                image_path = self._try_source(source, query, image_type, orientation, assets_dir)
                if image_path:
                    return image_path
            except Exception as e:
                print(f"   [pipeline] [{source}] error: {e}")
                continue

        return None

    def _try_source(self, source: str, query: str, image_type: str,
                     orientation: str, assets_dir: str) -> Optional[str]:
        if source not in self.image_search.services:
            return None

        if source == "pexels":
            results = self.image_search.search(
                query=query, source="stock", stock_service="pexels",
                count=1, orientation=orientation,
            )
            if not results:
                return None
            api = self.image_search.services["pexels"]
            safe_name = "".join(c if c.isalnum() else "_" for c in query[:30])
            save_path = os.path.join(assets_dir, f"pexels_{safe_name}.jpg")
            return self._download_first(results, api, save_path)

        video_theme = self.video_theme if self.video_theme else None
        if source == "real":
            results = self.image_search.search(
                query=query, source="real", count=1,
                orientation=orientation, video_theme=self.video_theme,
            )
        elif source == "exa":
            results = self.image_search.search(
                query=query, source="exa", count=1,
                orientation=orientation, video_theme=self.video_theme,
            )
        elif source == "tavily":
            results = self.image_search.search(
                query=query, source="tavily", count=1,
                orientation=orientation, video_theme=self.video_theme,
            )
        else:
            return None

        if not results:
            return None

        first = results[0]
        api = self.image_search.services.get(source)
        if not api:
            return None

        safe_name = "".join(c if c.isalnum() else "_" for c in query[:30])
        save_path = os.path.join(assets_dir, f"{source}_{safe_name}.jpg")
        return self._download_first([first], api, save_path)

    def _download_first(self, results: list, api, save_path: str) -> Optional[str]:
        for result in results:
            url = result.get("download_url", "")
            if not url:
                continue
            try:
                api.download(url, save_path)
                return save_path
            except Exception as e:
                print(f"   [pipeline] download error: {e}")
        return None

    def _check_and_refine_style(self, image_path: str, query: str,
                                 assets_dir: str, block_index: int,
                                 target_name: str = None) -> Optional[str]:
        if not self.video_theme or not self.validator:
            return image_path

        print(f"   [pipeline] style-check: {query[:50]}")
        result = self.validator.validate(
            image_path=image_path, query=query,
            video_theme=self.video_theme,
        )

        match_ok = result["match"] and result["confidence"] >= self.validator.confidence_threshold
        style_ok = result.get("style_match", True) and result.get("style_confidence", 0) >= self.validator.style_confidence_threshold

        print(f"   [pipeline] match={match_ok} ({result.get('confidence', 0):.2f}) "
              f"style={style_ok} ({result.get('style_confidence', 0):.2f})")

        if not match_ok:
            print(f"   [pipeline] object mismatch: {result.get('reason', 'N/A')}")
            return None

        if not style_ok:
            print(f"   [pipeline] style mismatch: {result.get('style_reason', 'N/A')}")
            refined = self._refine_image(image_path, query, assets_dir, block_index,
                                          target_name=target_name)
            if refined:
                try:
                    if os.path.exists(image_path) and refined != image_path:
                        os.remove(image_path)
                except OSError:
                    pass
                return refined
            print(f"   [pipeline] refine failed, using original")

        return image_path

    def _refine_image(self, image_path: str, query: str,
                       assets_dir: str, block_index: int,
                       target_name: str = None) -> Optional[str]:
        if not self.whisk_generator:
            print(f"   [pipeline] no Whisk generator, cannot refine")
            return None

        edit_instruction = HORROR_STYLE_PROMPT
        print(f"   [pipeline] Whisk refine (img2img): {query[:50]}")

        self.whisk_generator.output_dir = Path(assets_dir)
        try:
            saved_paths = self.whisk_generator.refine(
                image_path=image_path,
                edit_instruction=edit_instruction,
                caption=query,
            )
            if saved_paths and os.path.exists(saved_paths[0]):
                if target_name:
                    new_path = os.path.join(assets_dir, target_name)
                else:
                    base, _ = os.path.splitext(image_path)
                    new_path = base + "_refined.png"
                if os.path.exists(new_path):
                    os.remove(new_path)
                import shutil
                shutil.move(saved_paths[0], new_path)
                return new_path
        except Exception as e:
            print(f"   [pipeline] Whisk refine error: {e}")

        return None

    def generate_image(self, prompt: str, block_index: int,
                        assets_dir: str, asset_type: str = None,
                        max_retries: int = 3, target_name: str = None) -> Optional[str]:
        if not self.whisk_generator:
            print(f"   [pipeline] no Whisk generator")
            return None

        self.whisk_generator.output_dir = Path(assets_dir)
        cleaned_prompt = self._sanitize_prompt(prompt, asset_type)
        if cleaned_prompt != prompt:
            print(f"   [pipeline] sanitized: {cleaned_prompt}")
        print(f"   [pipeline] generating: {cleaned_prompt[:80]}")

        current_prompt = cleaned_prompt
        saved_paths = []

        for attempt in range(1, max_retries + 1):
            try:
                saved_paths = self.whisk_generator.generate(
                    prompt=current_prompt, model="IMAGEN_3_5",
                    aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE", seed=0, count=1
                )
                if saved_paths:
                    break
            except Exception as e:
                print(f"   [pipeline] Whisk error ({attempt}/{max_retries}): {e}")
                err = str(e).upper()
                if "PROMINENT_PEOPLE" in err or "PEOPLE_FILTER" in err or "PUBLIC_ERROR" in err:
                    current_prompt = self._anonymize_prompt(current_prompt, asset_type)
                    print(f"   [pipeline] retry with: {current_prompt}")
                elif "400" in str(e):
                    current_prompt = self._simplify_prompt(current_prompt)
                    print(f"   [pipeline] retry simplified: {current_prompt}")
                elif "COOKIE" in err or "ACCESS_TOKEN" in err:
                    break
                elif attempt < max_retries:
                    time.sleep(attempt * 5)

        if saved_paths and os.path.exists(saved_paths[0]):
            if target_name:
                new_path = os.path.join(assets_dir, target_name)
            else:
                safe = "".join(c if c.isalnum() else "_" for c in prompt[:40])
                prefix = asset_type or "generated"
                new_path = os.path.join(assets_dir, f"{prefix}_{safe}.png")
            if os.path.exists(new_path):
                os.remove(new_path)
            import shutil
            shutil.move(saved_paths[0], new_path)
            return new_path
        return None

    @staticmethod
    def _sanitize_prompt(prompt: str, asset_type: str = None) -> str:
        import re
        prominent = [
            "donald trump", "trump", "joe biden", "biden", "vladimir putin", "putin",
            "barack obama", "obama", "george bush", "bush", "bill clinton", "clinton",
            "elon musk", "musk", "jeff bezos", "bezos", "mark zuckerberg", "zuckerberg",
            "kim jong un", "kim jong", "xi jinping", "xi", "victor surge", "eric knudsen",
            "slenderman", "slender man", "jeff the killer", "sonic.exe", "herobrine",
            "adolf hitler", "hitler", "joseph stalin", "stalin", "winston churchill", "churchill",
            "saddam hussein", "saddam", "osama bin laden", "bin laden",
            "vladimir zelensky", "zelensky", "benjamin netanyahu", "netanyahu",
        ]
        sanitized = prompt
        lower = prompt.lower()
        for name in prominent:
            if name in lower:
                if asset_type in ("person", "person_photo"):
                    sanitized = re.sub(re.escape(name), "a person", sanitized, flags=re.IGNORECASE)
                else:
                    sanitized = re.sub(re.escape(name), "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        return sanitized

    @staticmethod
    def _anonymize_prompt(prompt: str, asset_type: str = None) -> str:
        import re
        if asset_type in ("person", "person_photo"):
            return "A professional portrait of a person in a studio setting, neutral background, photorealistic"
        if ":" in prompt:
            after = ":".join(prompt.split(":")[1:]).strip()
            if after:
                return after
        return re.sub(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', 'a person', prompt)

    @staticmethod
    def _simplify_prompt(prompt: str) -> str:
        import re
        simplified = re.sub(r'[^\w\s,.-]', '', prompt)
        words = simplified.split()
        if len(words) > 20:
            simplified = ' '.join(words[:20])
        return simplified.strip()

    def upscale_image(self, image_path: str, assets_dir: str,
                       block_index: int, target_name: str = None) -> str:
        if not self.upscaler_manager:
            return image_path

        esrgan = self.upscaler_manager.get_esrgan()
        enhancer = self.upscaler_manager.get_enhancer()

        try:
            if enhancer and UPSCALER_SD_CHECKPOINT:
                upscaled_path = esrgan.upscale_with_enhance(
                    image_path=image_path, save_path=None, outscale=None,
                    sd_checkpoint=UPSCALER_SD_CHECKPOINT,
                    sd_prompt=UPSCALER_SD_PROMPT,
                    sd_negative=UPSCALER_SD_NEGATIVE,
                    sd_strength=UPSCALER_SD_STRENGTH,
                    sd_steps=UPSCALER_SD_STEPS,
                    sd_guidance=UPSCALER_SD_GUIDANCE,
                    sd_sampler=UPSCALER_SD_SAMPLER,
                    sd_vae=UPSCALER_SD_VAE,
                    enhancer=enhancer,
                )
            else:
                upscaled_path = esrgan.upscale(
                    image_path=image_path, save_path=None, outscale=None,
                )

            if target_name:
                final_path = os.path.join(assets_dir, target_name)
            else:
                base, _ = os.path.splitext(image_path)
                final_path = base + ".png"
            if os.path.exists(upscaled_path) and upscaled_path != final_path:
                import shutil
                if os.path.exists(final_path):
                    os.remove(final_path)
                shutil.move(upscaled_path, final_path)
            if os.path.exists(image_path) and image_path != final_path:
                try:
                    os.remove(image_path)
                except OSError:
                    pass
            return final_path
        except Exception as e:
            print(f"   [pipeline] upscale error: {e}")
            return image_path
        finally:
            if enhancer:
                enhancer.unload()

    def cleanup(self):
        if self.upscaler_manager:
            self.upscaler_manager.cleanup()

import gc
import sys
import threading
from pathlib import Path
from typing import Optional, Dict

import numpy as np
import torch
from PIL import Image
from spandrel import ImageModelDescriptor, ModelLoader


MODELS_DIR = Path.home() / ".cache" / "realesrgan"
LOCAL_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class UpscaleManager:
    _instances: Dict[str, 'UpscaleManager'] = {}
    _lock = threading.Lock()

    def __init__(self, config: dict):
        self.config = config
        self._esrgan: Optional[ESRGANUpscaler] = None
        self._enhancer: Optional[Img2ImgEnhancer] = None
        self._lock_instance = threading.Lock()

    @classmethod
    def get_instance(cls, config_key: str = "default") -> 'UpscaleManager':
        if config_key not in cls._instances:
            with cls._lock:
                if config_key not in cls._instances:
                    from ..config import (
                        UPSCALER_MODEL, UPSCALER_MODEL_PATH, UPSCALER_SCALE,
                        UPSCALER_TILE, UPSCALER_GPU_ID, UPSCALER_HALF,
                        UPSCALER_GFPGAN, UPSCALER_SD_CHECKPOINT,
                        UPSCALER_SD_VAE,
                    )
                    config = {
                        "model_name": UPSCALER_MODEL,
                        "model_path": UPSCALER_MODEL_PATH or None,
                        "scale": int(UPSCALER_SCALE) if UPSCALER_SCALE else None,
                        "tile": UPSCALER_TILE,
                        "gpu_id": UPSCALER_GPU_ID,
                        "half": UPSCALER_HALF,
                        "gfpgan_path": UPSCALER_GFPGAN or None,
                        "sd_checkpoint": UPSCALER_SD_CHECKPOINT or None,
                        "sd_vae": UPSCALER_SD_VAE or None,
                    }
                    cls._instances[config_key] = cls(config)
        return cls._instances[config_key]

    def get_esrgan(self) -> 'ESRGANUpscaler':
        if self._esrgan is None:
            with self._lock_instance:
                if self._esrgan is None:
                    self._esrgan = ESRGANUpscaler(
                        model_name=self.config["model_name"],
                        model_path=self.config["model_path"],
                        scale=self.config["scale"],
                        tile=self.config["tile"],
                        gpu_id=self.config["gpu_id"],
                        half=self.config["half"],
                        gfpgan_path=self.config["gfpgan_path"],
                    )
        return self._esrgan

    def get_enhancer(self) -> Optional['Img2ImgEnhancer']:
        if not self.config["sd_checkpoint"]:
            return None
        if self._enhancer is None:
            with self._lock_instance:
                if self._enhancer is None:
                    self._enhancer = Img2ImgEnhancer(
                        checkpoint=self.config["sd_checkpoint"],
                        gpu_id=self.config["gpu_id"],
                        half=self.config["half"],
                        vae=self.config["sd_vae"],
                    )
        return self._enhancer

    def cleanup(self):
        with self._lock_instance:
            if self._esrgan:
                self._esrgan.cleanup()
                self._esrgan = None
            if self._enhancer:
                self._enhancer.unload()
                self._enhancer = None

    @classmethod
    def cleanup_all(cls):
        for instance in cls._instances.values():
            instance.cleanup()
        cls._instances.clear()

BUILTIN_MODELS = {
    "4x-ultrasharp": {
        "scale": 4,
        "file": "4x-UltraSharp.pth",
        "url": "",
    },
    "realesrgan-x4plus": {
        "scale": 4,
        "file": "realesrgan_x4plus.pth",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    },
    "realesrgan-x4plus-anime": {
        "scale": 4,
        "file": "realesrgan_x4plus_anime_6B.pth",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
    },
    "realesrgan-x2plus": {
        "scale": 2,
        "file": "realesrgan_x2plus.pth",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
    },
    "realesrgan-general-x4v3": {
        "scale": 4,
        "file": "realesrgan-general-x4v3.pth",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.3.0/RealESRGAN-General-x4v3.pth",
    },
}


def _download_model(url: str, filename: str) -> str:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = MODELS_DIR / filename
    if target.exists():
        return str(target)

    import requests

    print(f"  Downloading {filename}...")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(target, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                progress = downloaded / total * 100
                print(f"\r  {progress:.0f}%", end="", flush=True)

    print(f"\n  Downloaded: {target}")
    return str(target)


def _pil_to_tensor(img: Image.Image) -> torch.Tensor:
    arr = np.array(img.convert("RGB")).astype(np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)


def _tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    arr = tensor.squeeze(0).permute(1, 2, 0).cpu().clamp(0, 1).numpy()
    arr = (arr * 255).round().astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _create_feather_mask(height: int, width: int, feather: int) -> torch.Tensor:
    mask = torch.ones(1, 1, height, width, dtype=torch.float32)

    if feather <= 0:
        return mask

    for i in range(feather):
        alpha = (i + 1) / feather
        if i < height:
            mask[:, :, i, :] *= alpha
            mask[:, :, -(i + 1), :] *= alpha
        if i < width:
            mask[:, :, :, i] *= alpha
            mask[:, :, :, -(i + 1)] *= alpha

    return mask


@torch.inference_mode()
def _tiled_upscale(
    img_tensor: torch.Tensor,
    model: ImageModelDescriptor,
    tile_size: int = 512,
    tile_overlap: int = 32,
    device: torch.device = torch.device("cuda"),
    model_dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    scale_factor = model.scale
    _, channels, in_h, in_w = img_tensor.shape
    out_h = in_h * scale_factor
    out_w = in_w * scale_factor

    output = torch.zeros(1, channels, out_h, out_w, dtype=torch.float32, device="cpu")
    weight_sum = torch.zeros(1, 1, out_h, out_w, dtype=torch.float32, device="cpu")

    stride = tile_size - tile_overlap
    feather = tile_overlap * scale_factor

    y_positions = list(range(0, max(1, in_h - tile_size), stride))
    if not y_positions or y_positions[-1] + tile_size < in_h:
        y_positions.append(max(0, in_h - tile_size))

    x_positions = list(range(0, max(1, in_w - tile_size), stride))
    if not x_positions or x_positions[-1] + tile_size < in_w:
        x_positions.append(max(0, in_w - tile_size))

    total_tiles = len(y_positions) * len(x_positions)
    current_tile = 0

    for y_pos in y_positions:
        for x_pos in x_positions:
            current_tile += 1

            tile_h = min(tile_size, in_h - y_pos)
            tile_w = min(tile_size, in_w - x_pos)

            tile = img_tensor[:, :, y_pos:y_pos + tile_h, x_pos:x_pos + tile_w]
            tile = tile.to(device=device, dtype=model_dtype)

            out_tile = model(tile).cpu()

            mask = _create_feather_mask(
                out_tile.shape[2],
                out_tile.shape[3],
                feather
            )

            out_y = y_pos * scale_factor
            out_x = x_pos * scale_factor
            tile_out_h = out_tile.shape[2]
            tile_out_w = out_tile.shape[3]

            output[:, :, out_y:out_y + tile_out_h, out_x:out_x + tile_out_w] += out_tile * mask
            weight_sum[:, :, out_y:out_y + tile_out_h, out_x:out_x + tile_out_w] += mask

            del tile, out_tile, mask
            print(f"\r  Tile {current_tile}/{total_tiles}", end="", flush=True)

    print()
    output = output / weight_sum.clamp(min=1e-8)
    return output


class ESRGANUpscaler:
    def __init__(
        self,
        model_name: str = "4x-ultrasharp",
        model_path: Optional[str] = None,
        scale: Optional[int] = None,
        tile: int = 512,
        tile_overlap: int = 32,
        half: bool = True,
        gpu_id: int = 0,
        gfpgan_path: Optional[str] = None,
    ):
        self.model_name = model_name
        self.model_path = model_path
        self.scale = scale
        self.tile = tile
        self.tile_overlap = tile_overlap
        self.half = half
        self.gpu_id = gpu_id
        self.gfpgan_path = gfpgan_path
        self._model: Optional[ImageModelDescriptor] = None
        self._device: Optional[torch.device] = None

    @property
    def device(self) -> torch.device:
        if self._device is None:
            self._device = torch.device(
                f"cuda:{self.gpu_id}" if torch.cuda.is_available() else "cpu"
            )
            if self._device.type == "cpu":
                self.half = False
        return self._device

    def _resolve_model_path(self) -> str:
        if self.model_path and Path(self.model_path).exists():
            return self.model_path

        if self.model_name not in BUILTIN_MODELS:
            self.scale = self.scale or 4
            return ""

        cfg = BUILTIN_MODELS[self.model_name]
        self.scale = self.scale or cfg.get("scale", 4)

        local_path = LOCAL_MODELS_DIR / cfg["file"]
        if local_path.exists():
            return str(local_path)

        cache_path = MODELS_DIR / cfg["file"]
        if cache_path.exists():
            return str(cache_path)

        if cfg.get("url"):
            return _download_model(cfg["url"], cfg["file"])

        raise FileNotFoundError(
            f"Model '{cfg['file']}' not found.\n"
            f"Expected locations:\n"
            f"  - {local_path}\n"
            f"  - {cache_path}"
        )

    def load_model(self):
        if self._model is not None:
            return

        model_path = self._resolve_model_path()
        if not model_path:
            raise ValueError("No model path specified and model_name is not in BUILTIN_MODELS")

        print(f"  Loading ESRGAN model: {model_path}")

        model = ModelLoader(device="cpu").load_from_file(model_path)
        if not isinstance(model, ImageModelDescriptor):
            raise TypeError(f"Expected ImageModelDescriptor, got {type(model)}")

        if self.half and self.device.type == "cuda" and model.supports_half:
            model.half()

        model.to(self.device).eval()
        self.scale = model.scale
        self._model = model

        print(f"  Loaded: {Path(model_path).name} (x{self.scale}, {self.device})")

    def upscale(
        self,
        image_path: str,
        save_path: Optional[str] = None,
        outscale: Optional[float] = None,
        gfpgan: bool = False,
    ) -> str:
        self.load_model()

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        print(f"  Input: {orig_w}x{orig_h}")

        img_tensor = _pil_to_tensor(img)

        effective_scale = outscale if outscale is not None else self.scale

        model_dtype = torch.float16 if self.half and self.device.type == "cuda" and self._model.supports_half else torch.float32

        if self.tile <= 0:
            result_tensor = self._model(
                img_tensor.to(self.device, dtype=model_dtype)
            ).cpu()
        else:
            result_tensor = _tiled_upscale(
                img_tensor,
                self._model,
                tile_size=self.tile,
                tile_overlap=self.tile_overlap,
                device=self.device,
                model_dtype=model_dtype,
            )

        result = _tensor_to_pil(result_tensor)

        if effective_scale != self.scale:
            target_w = int(orig_w * effective_scale)
            target_h = int(orig_h * effective_scale)
            result = result.resize((target_w, target_h), Image.LANCZOS)

        if gfpgan and self.gfpgan_path:
            result = self._apply_gfpgan(result)

        if save_path is None:
            src = Path(image_path)
            suffix = "_upscaled" if outscale is None else f"_x{outscale}"
            save_path = str(src.parent / f"{src.stem}{suffix}.png")

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        result.save(save_path)

        final_w, final_h = result.size
        print(f"  Output: {final_w}x{final_h} -> {save_path}")
        return save_path

    def upscale_with_enhance(
        self,
        image_path: str,
        save_path: Optional[str] = None,
        outscale: Optional[float] = None,
        sd_checkpoint: Optional[str] = None,
        sd_prompt: Optional[str] = None,
        sd_negative: Optional[str] = None,
        sd_strength: float = 0.13,
        sd_steps: int = 6,
        sd_guidance: float = 2.0,
        sd_sampler: str = "DPM++ SDE Karras",
        sd_seed: int = -1,
        sd_vae: Optional[str] = None,
        enhancer: Optional['Img2ImgEnhancer'] = None,
    ) -> str:
        default_prompt = "highly detailed vibrant colors, 4k"
        default_negative = "low quality, blurry, jpeg artifacts, noise, grain, oversharpened, artifacts, deformed"

        prompt = sd_prompt or default_prompt
        negative = sd_negative or default_negative

        src_img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = src_img.size
        print(f"  Input: {orig_w}x{orig_h}")

        print(f"  Pass 1: SD img2img enhancement")
        print(f"    checkpoint: {sd_checkpoint}")
        print(f"    prompt: {prompt}")
        print(f"    strength: {sd_strength}, steps: {sd_steps}, cfg: {sd_guidance}, sampler: {sd_sampler}")

        if enhancer is None:
            enhancer = Img2ImgEnhancer(
                checkpoint=sd_checkpoint,
                gpu_id=self.gpu_id,
                half=self.half,
                vae=sd_vae,
            )
            cleanup_enhancer = True
        else:
            cleanup_enhancer = False

        try:
            enhanced = enhancer.enhance(
                image=src_img,
                prompt=prompt,
                negative_prompt=negative,
                strength=sd_strength,
                steps=sd_steps,
                guidance_scale=sd_guidance,
                sampler=sd_sampler,
                seed=sd_seed,
            )
        finally:
            if cleanup_enhancer:
                enhancer.unload()

        enh_w, enh_h = enhanced.size
        print(f"    Enhanced: {enh_w}x{enh_h}")

        temp_path = Path(image_path).parent / f"{Path(image_path).stem}_sd_temp.png"
        enhanced.save(str(temp_path))

        try:
            effective_scale = outscale if outscale is not None else self.scale
            print(f"  Pass 2: ESRGAN upscale (x{effective_scale or '?'})")

            esrgan_output = self.upscale(
                image_path=str(temp_path),
                save_path=None,
                outscale=outscale,
            )

            if save_path is None:
                src = Path(image_path)
                suffix = "_enhanced" if outscale is None else f"_x{outscale}_enhanced"
                save_path = str(src.parent / f"{src.stem}{suffix}.png")

            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            Path(esrgan_output).rename(save_path)

            final_img = Image.open(save_path)
            final_w, final_h = final_img.size
            print(f"  Final: {final_w}x{final_h} -> {save_path}")

            return save_path
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def upscale_batch(
        self,
        image_paths: list[str],
        output_dir: Optional[str] = None,
        outscale: Optional[float] = None,
        gfpgan: bool = False,
    ) -> list[str]:
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = []
        total = len(image_paths)

        for idx, img_path in enumerate(image_paths, 1):
            print(f"Upscaling [{idx}/{total}]: {img_path}")
            src = Path(img_path)

            if output_dir:
                suffix = "_upscaled" if outscale is None else f"_x{outscale}"
                save_path = str(Path(output_dir) / f"{src.stem}{suffix}.png")
            else:
                save_path = None

            try:
                result = self.upscale(
                    image_path=img_path,
                    save_path=save_path,
                    outscale=outscale,
                    gfpgan=gfpgan,
                )
                results.append(result)
            except Exception as e:
                print(f"  Failed: {e}")
                results.append(None)

        return results

    def _apply_gfpgan(self, img: Image.Image) -> Image.Image:
        import cv2
        from gfpgan import GFPGANer

        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        face_enhancer = GFPGANer(
            model_path=self.gfpgan_path,
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            device=self.device,
        )

        _, _, output = face_enhancer.enhance(
            img_np,
            has_aligned=False,
            only_center_face=False,
            paste_back=True,
        )

        return Image.fromarray(cv2.cvtColor(output, cv2.COLOR_BGR2RGB))

    @staticmethod
    def list_builtin_models() -> list[str]:
        return list(BUILTIN_MODELS.keys())

    @staticmethod
    def scan_model_dir(directory: str) -> list[str]:
        d = Path(directory)
        if not d.exists():
            return []
        return sorted(str(p) for p in d.glob("*.pth"))

    def cleanup(self):
        if self._model is not None:
            del self._model
            self._model = None
        if self._device is not None and self._device.type == "cuda":
            torch.cuda.empty_cache()
            gc.collect()


class Img2ImgEnhancer:
    def __init__(
        self,
        checkpoint: str,
        gpu_id: int = 0,
        half: bool = True,
        vae: Optional[str] = None,
    ):
        self.checkpoint = checkpoint
        self.gpu_id = gpu_id
        self.half = half
        self.vae = vae
        self._pipe = None
        self._device: Optional[torch.device] = None

    @property
    def device(self) -> torch.device:
        if self._device is None:
            self._device = torch.device(
                f"cuda:{self.gpu_id}" if torch.cuda.is_available() else "cpu"
            )
        return self._device

    def _init_pipe(self):
        if self._pipe is not None:
            return

        dtype = torch.float16 if self.half and self.device.type == "cuda" else torch.float32
        print(f"  Loading SD checkpoint: {self.checkpoint}")

        load_kwargs = {"torch_dtype": dtype}

        if self.vae:
            from diffusers import AutoencoderKL
            load_kwargs["vae"] = AutoencoderKL.from_single_file(self.vae, torch_dtype=torch.float32)

        try:
            from diffusers import StableDiffusionXLImg2ImgPipeline
        except ImportError:
            try:
                from diffusers import StableDiffusionImg2ImgPipeline
                print("  Warning: Using StableDiffusionImg2ImgPipeline instead of XL version")
                StableDiffusionXLImg2ImgPipeline = StableDiffusionImg2ImgPipeline
            except ImportError:
                raise ImportError(
                    "Neither StableDiffusionXLImg2ImgPipeline nor StableDiffusionImg2ImgPipeline found. "
                    "Install diffusers: pip install diffusers transformers accelerate"
                )

        self._pipe = StableDiffusionXLImg2ImgPipeline.from_single_file(
            self.checkpoint,
            **load_kwargs,
        )

        self._pipe = self._pipe.to(self.device)
        self._pipe.safety_checker = None
        self._pipe.requires_safety_checker = False

        if self._pipe.vae is not None:
            self._pipe.vae = self._pipe.vae.to(torch.float32)

        print(f"  SD model loaded ({'fp16' if self.half else 'fp32'}, {self.device})")

    def _set_scheduler(self, sampler_name: str):
        from diffusers import (
            DPMSolverMultistepScheduler,
            DPMSolverSinglestepScheduler,
            EulerAncestralDiscreteScheduler,
            EulerDiscreteScheduler,
            KDPM2AncestralDiscreteScheduler,
            KDPM2DiscreteScheduler,
            LMSDiscreteScheduler,
            PNDMScheduler,
            UniPCMultistepScheduler,
        )

        sampler_map = {
            "euler": EulerDiscreteScheduler,
            "euler a": EulerAncestralDiscreteScheduler,
            "euler_ancestral": EulerAncestralDiscreteScheduler,
            "dpm++ sde": DPMSolverSinglestepScheduler,
            "dpm++ sde karras": DPMSolverSinglestepScheduler,
            "dpm++ 2m": DPMSolverMultistepScheduler,
            "dpm++ 2m karras": DPMSolverMultistepScheduler,
            "dpm2 a": KDPM2AncestralDiscreteScheduler,
            "dpm2": KDPM2DiscreteScheduler,
            "lms": LMSDiscreteScheduler,
            "lms karras": LMSDiscreteScheduler,
            "pndm": PNDMScheduler,
            "unipc": UniPCMultistepScheduler,
        }

        key = sampler_name.lower().strip()
        sched_class = sampler_map.get(key, DPMSolverSinglestepScheduler)
        config = self._pipe.scheduler.config

        scheduler_kwargs = {}
        if "dpm++ sde" in key and issubclass(sched_class, DPMSolverSinglestepScheduler):
            scheduler_kwargs["algorithm_type"] = "sde-dpmsolver++"
            scheduler_kwargs["lower_order_final"] = True
        if "karras" in key:
            scheduler_kwargs["use_karras_sigmas"] = True

        self._pipe.scheduler = sched_class.from_config(config, **scheduler_kwargs)
        print(f"  Scheduler: {sampler_name}")

    @torch.inference_mode()
    def enhance(
        self,
        image: Image.Image,
        prompt: str = "highly detailed vibrant colors, 4k",
        negative_prompt: str = "low quality, blurry, jpeg artifacts, noise, grain, oversharpened, artifacts, deformed",
        strength: float = 0.13,
        steps: int = 6,
        guidance_scale: float = 2.0,
        sampler: str = "DPM++ SDE Karras",
        seed: int = -1,
    ) -> Image.Image:
        self._init_pipe()
        self._set_scheduler(sampler)

        w, h = image.size
        new_w = w - (w % 8)
        new_h = h - (h % 8)

        if new_w != w or new_h != h:
            image = image.resize((new_w, new_h), Image.LANCZOS)

        if max(new_w, new_h) > 2048:
            scale_down = 2048 / max(new_w, new_h)
            new_w = int(new_w * scale_down)
            new_h = int(new_h * scale_down)
            new_w = new_w - (new_w % 8)
            new_h = new_h - (new_h % 8)
            print(f"  Resizing image from {w}x{h} to {new_w}x{new_h} for SDXL compatibility")
            image = image.resize((new_w, new_h), Image.LANCZOS)

        min_steps = max(1, int(strength * steps) + 1)
        if steps < min_steps:
            print(f"  Warning: steps={steps} too low for strength={strength}, using {min_steps}")
            steps = min_steps

        generator = None
        if seed >= 0:
            generator = torch.Generator(device="cpu").manual_seed(seed)

        result = self._pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=image,
            strength=strength,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
            original_size=(new_w, new_h),
            target_size=(new_w, new_h),
            output_type="pil",
        ).images[0]

        return result

    def unload(self):
        if self._pipe is not None:
            del self._pipe
            self._pipe = None
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
            gc.collect()

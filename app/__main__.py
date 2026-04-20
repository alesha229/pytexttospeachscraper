import argparse
import os
import sys


def _resolve_context(args):
    context = getattr(args, 'context', None)
    context_file = getattr(args, 'context_file', None)
    if context_file:
        with open(context_file, "r", encoding="utf-8") as f:
            context = f.read().strip()
    return context or None


def main():
    parser = argparse.ArgumentParser(
        description="PyTTS Video Pipeline - automated video + AE project generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  generate    Full video generation (scenario -> assets -> audio -> video + AE project)
  scenario    Generate scenario only (JSON)
  ae-project  Generate AE project JSON from existing project directory
  tts         Generate speech from text

Examples:
  python -m app generate "Space Exploration"
  python -m app generate "Cyberpunk" --duration 60 --style cinematic
  python -m app scenario "History of Rome" --language en
  python -m app ae-project ./video_output_v2/MyTopic_123456
  python -m app tts "Hello world" --voice Blake --output out.wav
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate complete video with AE project")
    gen_parser.add_argument("topic", type=str, help="Video topic/theme")
    gen_parser.add_argument("--duration", type=int, default=30, help="Target duration in seconds (supports 1h+ videos, e.g. 3600)")
    gen_parser.add_argument("--style", type=str, default=None, help="Video style")
    gen_parser.add_argument("--language", type=str, default="en", help="Language (en, ru)")
    gen_parser.add_argument("--scenes", type=int, default=None, help="Number of scenes (ignored for long videos, use --chunk-duration instead)")
    gen_parser.add_argument("--chunk-duration", type=int, default=None, help="Chapter duration in seconds for long videos (default 300)")
    gen_parser.add_argument("--output", type=str, default=None, help="Output video filename")
    gen_parser.add_argument("--no-ae", action="store_true", help="Skip AE project generation")
    gen_parser.add_argument("--fast", action="store_true", help="Fast render (lower quality)")
    gen_parser.add_argument("--cpu", action="store_true", help="Use CPU instead of GPU")
    gen_parser.add_argument("--fireworks-key", type=str, default=None)
    gen_parser.add_argument("--whisk-cookie", type=str, default=None)
    gen_parser.add_argument("--pexels-key", type=str, default=None)
    gen_parser.add_argument("--use-stock", action="store_true", help="Use Pexels stock photos")
    gen_parser.add_argument("--no-real", action="store_true", help="Skip real photos (DuckDuckGo)")
    gen_parser.add_argument("--no-validate", action="store_true", help="Skip Qwen VL image validation")
    gen_parser.add_argument("--assets-only", action="store_true", help="Generate assets only (no video assembly)")
    gen_parser.add_argument("--context", type=str, default=None, help="Context data (news/facts) for the script")
    gen_parser.add_argument("--context-file", type=str, default=None, help="File with context data for the script")
    gen_parser.add_argument("--no-upscale", action="store_true", help="Disable ESRGAN upscaling of generated images")

    # scenario
    scen_parser = subparsers.add_parser("scenario", help="Generate scenario JSON")
    scen_parser.add_argument("topic", type=str, help="Video topic/theme")
    scen_parser.add_argument("--duration", type=int, default=30, help="Target duration (seconds)")
    scen_parser.add_argument("--style", type=str, default=None, help="Video style")
    scen_parser.add_argument("--language", type=str, default="en", help="Language")
    scen_parser.add_argument("--scenes", type=int, default=None, help="Number of scenes")
    scen_parser.add_argument("--chunk-duration", type=int, default=None, help="Chapter duration in seconds for long videos (default 300)")
    scen_parser.add_argument("--output", "-o", type=str, default=None, help="Output JSON file")
    scen_parser.add_argument("--refine", "-r", type=str, default=None, help="Scenario file to refine")
    scen_parser.add_argument("--feedback", "-f", type=str, default=None, help="Feedback for refinement")
    scen_parser.add_argument("--context", type=str, default=None, help="Context data (news/facts) for the script")
    scen_parser.add_argument("--context-file", type=str, default=None, help="File with context data for the script")
    scen_parser.add_argument("--fireworks-key", type=str, default=None)

    # ae-project
    ae_parser = subparsers.add_parser("ae-project", help="Generate AE project JSON from project directory")
    ae_parser.add_argument("project_dir", help="Project directory with scenario.json + assets/ + audio/")
    ae_parser.add_argument("--montage-config", type=str, default=None, help="Custom montage config JSON")

    # tts
    tts_parser = subparsers.add_parser("tts", help="Generate speech from text")
    tts_parser.add_argument("text", type=str, help="Text to synthesize")
    tts_parser.add_argument("--voice", type=str, default=None, help="Voice ID or name (default from config)")
    tts_parser.add_argument("--output", type=str, default="output.wav", help="Output WAV file")
    tts_parser.add_argument("--max-chars", type=int, default=1000, help="Max chars per chunk")
    tts_parser.add_argument("--list-voices", action="store_true", help="List available voices")

    # upscale
    up_parser = subparsers.add_parser("upscale", help="Upscale images via ESRGAN + SD img2img")
    up_parser.add_argument("images", nargs="*", help="Image file(s) or directory")
    up_parser.add_argument("--model", type=str, default=None, help="ESRGAN model name")
    up_parser.add_argument("--model-path", type=str, default=None, help="Path to custom .pth ESRGAN model")
    up_parser.add_argument("--scale", type=float, default=None, help="Output scale factor (default from model)")
    up_parser.add_argument("--tile", type=int, default=None, help="Tile size for GPU memory (0=off, default 512)")
    up_parser.add_argument("--tile-overlap", type=int, default=None, help="Tile overlap for seamless blending (default 32)")
    up_parser.add_argument("--gpu", type=int, default=None, help="GPU device id (default 0)")
    up_parser.add_argument("--fp32", action="store_true", help="Use full precision")
    up_parser.add_argument("--gfpgan", action="store_true", help="Enable GFPGAN face restoration")
    up_parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    up_parser.add_argument("--list-models", action="store_true", help="List built-in models and exit")
    up_parser.add_argument("--scan-dir", type=str, default=None, help="Scan directory for .pth model files")
    up_parser.add_argument("--enhance", action="store_true", help="Add SD img2img pass for detail enhancement")
    up_parser.add_argument("--sd-checkpoint", type=str, default=None, help="Path to SD .safetensors/.ckpt checkpoint")
    up_parser.add_argument("--sd-prompt", type=str, default=None, help="Prompt for img2img enhancement")
    up_parser.add_argument("--sd-negative", type=str, default=None, help="Negative prompt for img2img")
    up_parser.add_argument("--sd-strength", type=float, default=None, help="Denoising strength 0.1-1.0 (default 0.13)")
    up_parser.add_argument("--sd-steps", type=int, default=None, help="Inference steps (default 6)")
    up_parser.add_argument("--sd-guidance", type=float, default=None, help="CFG guidance scale (default 2.0)")
    up_parser.add_argument("--sd-seed", type=int, default=None, help="Seed (-1 = random)")
    up_parser.add_argument("--sd-vae", type=str, default=None, help="Path to custom VAE .safetensors")
    up_parser.add_argument("--sd-sampler", type=str, default=None, help="Sampler (DPM++ SDE Karras, Euler a, etc.)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "scenario":
        _cmd_scenario(args)
    elif args.command == "ae-project":
        _cmd_ae_project(args)
    elif args.command == "tts":
        _cmd_tts(args)
    elif args.command == "upscale":
        _cmd_upscale(args)


def _cmd_generate(args):
    from .core.video import VideoGeneratorV2
    from .config import TTS_DEFAULT_VOICE_ID, SCENARIO_CHUNK_DURATION

    if args.chunk_duration:
        import os as _os
        _os.environ["SCENARIO_CHUNK_DURATION"] = str(args.chunk_duration)

    fireworks_key = args.fireworks_key or os.environ.get("FIREWORKS_API_KEY")
    whisk_cookie = args.whisk_cookie or os.environ.get("WHISK_COOKIE")
    pexels_key = args.pexels_key or os.environ.get("PEXELS_API_KEY")

    if not fireworks_key:
        print("Warning: FIREWORKS_API_KEY not set")
    if not whisk_cookie:
        print("Warning: WHISK_COOKIE not set")

    generator = VideoGeneratorV2(
        fireworks_api_key=fireworks_key,
        whisk_cookie=whisk_cookie,
        pexels_api_key=pexels_key,
        voice_id=TTS_DEFAULT_VOICE_ID,
        use_real_photos=not args.no_real,
        use_stock_photos=args.use_stock,
        validate_images=not args.no_validate,
        enable_upscale=not args.no_upscale,
    )

    if args.assets_only:
        result = generator.generate_assets_only(
            topic=args.topic,
            language=args.language,
            duration=args.duration,
            style=args.style,
            num_scenes=args.scenes,
            context=_resolve_context(args),
        )
        print(f"\nAssets ready: {result}")
    else:
        result = generator.generate_video(
            topic=args.topic,
            language=args.language,
            duration=args.duration,
            style=args.style,
            num_scenes=args.scenes,
            video_filename=args.output,
            fast=args.fast,
            use_gpu=not args.cpu,
            generate_ae=not args.no_ae,
            context=_resolve_context(args),
        )
        print(f"\nVideo ready: {result}")


def _cmd_scenario(args):
    from .core.scenario import VideoScenarioPlannerV2

    if args.chunk_duration:
        import os as _os
        _os.environ["SCENARIO_CHUNK_DURATION"] = str(args.chunk_duration)

    fireworks_key = args.fireworks_key or os.environ.get("FIREWORKS_API_KEY")
    planner = VideoScenarioPlannerV2(api_key=fireworks_key)

    if args.refine and args.feedback:
        print(f"Refining scenario: {args.refine}")
        scenario = planner.load_scenario(args.refine)
        scenario = planner.refine_scenario(scenario, args.feedback)
        planner.print_scenario(scenario)
        output_file = args.output or f"scenario_v2_{args.topic[:30].replace(' ', '_')}.json"
        planner.save_scenario(scenario, output_file)
    else:
        print(f"Creating scenario: {args.topic}")
        scenario = planner.create_scenario(
            topic=args.topic,
            language=args.language,
            target_duration=args.duration,
            style=args.style,
            num_scenes=args.scenes,
            context=_resolve_context(args),
        )
        planner.print_scenario(scenario)
        output_file = args.output or f"scenario_v2_{args.topic[:30].replace(' ', '_')}.json"
        planner.save_scenario(scenario, output_file)


def _cmd_ae_project(args):
    from .core.ae_project import AEJsonGenerator

    gen = AEJsonGenerator(montage_config_path=args.montage_config)
    json_path = gen.generate_from_project_dir(args.project_dir)
    print(f"\nAE project generated: {json_path}")


def _cmd_tts(args):
    from .core.tts import tts, list_voices
    from .config import TTS_DEFAULT_VOICE_ID

    if args.list_voices:
        list_voices()
        return

    if not args.text:
        print("Error: text required")
        sys.exit(1)

    voice = args.voice or TTS_DEFAULT_VOICE_ID
    success = tts(
        text=args.text,
        voice_id=voice,
        output_path=args.output,
        max_chunk=args.max_chars,
    )
    if success:
        print(f"\nAudio saved: {args.output}")
    else:
        print("\nFailed to generate audio")
        sys.exit(1)


def _cmd_upscale(args):
    from pathlib import Path as _Path
    import importlib
    _upscaler_mod = importlib.import_module("app.images.upscaler")
    ESRGANUpscaler = _upscaler_mod.ESRGANUpscaler
    from .config import (
        UPSCALER_MODEL, UPSCALER_MODEL_PATH, UPSCALER_SCALE,
        UPSCALER_TILE, UPSCALER_GPU_ID, UPSCALER_HALF,
        UPSCALER_GFPGAN, UPSCALER_MODEL_DIR,
        UPSCALER_SD_CHECKPOINT, UPSCALER_SD_PROMPT, UPSCALER_SD_NEGATIVE,
        UPSCALER_SD_STRENGTH, UPSCALER_SD_STEPS, UPSCALER_SD_GUIDANCE,
        UPSCALER_SD_VAE, UPSCALER_SD_SAMPLER,
    )

    if args.list_models:
        print("Built-in models:")
        for name in ESRGANUpscaler.list_builtin_models():
            print(f"  {name}")
        if UPSCALER_MODEL_DIR:
            found = ESRGANUpscaler.scan_model_dir(UPSCALER_MODEL_DIR)
            if found:
                print(f"\nCustom models in {UPSCALER_MODEL_DIR}:")
                for p in found:
                    print(f"  {p}")
        return

    if args.scan_dir:
        found = ESRGANUpscaler.scan_model_dir(args.scan_dir)
        if found:
            print(f"Models in {args.scan_dir}:")
            for p in found:
                print(f"  {p}")
        else:
            print("No .pth files found")
        return

    image_paths = []
    for path in args.images:
        p = _Path(path)
        if p.is_dir():
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"):
                image_paths.extend(str(x) for x in p.glob(ext))
        elif p.exists():
            image_paths.append(str(p))
        else:
            print(f"Warning: {path} not found")

    if not image_paths:
        print("No images found")
        sys.exit(1)

    upscaler = ESRGANUpscaler(
        model_name=args.model or UPSCALER_MODEL,
        model_path=args.model_path or UPSCALER_MODEL_PATH or None,
        scale=int(args.scale) if args.scale else None,
        tile=args.tile or UPSCALER_TILE,
        tile_overlap=args.tile_overlap if args.tile_overlap is not None else 32,
        half=not args.fp32 if args.fp32 else UPSCALER_HALF,
        gpu_id=args.gpu if args.gpu is not None else UPSCALER_GPU_ID,
        gfpgan_path=UPSCALER_GFPGAN or None,
    )

    outscale = args.scale if args.scale else None
    enhance = args.enhance or bool(UPSCALER_SD_CHECKPOINT)
    sd_checkpoint = args.sd_checkpoint or UPSCALER_SD_CHECKPOINT

    print(f"Upscaling {len(image_paths)} image(s)...")

    if enhance and not sd_checkpoint:
        print("Error: --enhance requires --sd-checkpoint or UPSCALER_SD_CHECKPOINT in .env")
        sys.exit(1)

    if enhance:
        for i, img_path in enumerate(image_paths, 1):
            print(f"[{i}/{len(image_paths)}] {img_path}")
            p = _Path(img_path)
            if args.output_dir:
                suffix = "_enhanced" if outscale is None else f"_x{outscale}_enhanced"
                save_path = str(_Path(args.output_dir) / f"{p.stem}{suffix}.png")
            else:
                save_path = None
            result = upscaler.upscale_with_enhance(
                image_path=img_path,
                save_path=save_path,
                outscale=outscale,
                sd_checkpoint=sd_checkpoint,
                sd_prompt=args.sd_prompt or UPSCALER_SD_PROMPT or None,
                sd_negative=args.sd_negative or UPSCALER_SD_NEGATIVE or None,
                sd_strength=args.sd_strength if args.sd_strength is not None else UPSCALER_SD_STRENGTH,
                sd_steps=args.sd_steps if args.sd_steps is not None else UPSCALER_SD_STEPS,
                sd_guidance=args.sd_guidance if args.sd_guidance is not None else UPSCALER_SD_GUIDANCE,
                sd_seed=args.sd_seed if args.sd_seed is not None else -1,
                sd_vae=args.sd_vae or UPSCALER_SD_VAE or None,
                sd_sampler=args.sd_sampler or UPSCALER_SD_SAMPLER,
            )
            print(f"Done: {result}")
    elif len(image_paths) == 1:
        result = upscaler.upscale(
            image_path=image_paths[0],
            outscale=outscale,
            gfpgan=args.gfpgan,
        )
        print(f"Done: {result}")
    else:
        results = upscaler.upscale_batch(
            image_paths=image_paths,
            output_dir=args.output_dir,
            outscale=outscale,
            gfpgan=args.gfpgan,
        )
        done = sum(1 for r in results if r)
        print(f"\nDone: {done}/{len(results)} images upscaled")


if __name__ == "__main__":
    main()

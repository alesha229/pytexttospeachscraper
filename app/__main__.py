import argparse
import os
import sys


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
    gen_parser.add_argument("--duration", type=int, default=30, help="Target duration (seconds)")
    gen_parser.add_argument("--style", type=str, default=None, help="Video style")
    gen_parser.add_argument("--language", type=str, default="en", help="Language (en, ru)")
    gen_parser.add_argument("--scenes", type=int, default=None, help="Number of scenes")
    gen_parser.add_argument("--output", type=str, default=None, help="Output video filename")
    gen_parser.add_argument("--no-ae", action="store_true", help="Skip AE project generation")
    gen_parser.add_argument("--fast", action="store_true", help="Fast render (lower quality)")
    gen_parser.add_argument("--cpu", action="store_true", help="Use CPU instead of GPU")
    gen_parser.add_argument("--fireworks-key", type=str, default=None)
    gen_parser.add_argument("--whisk-cookie", type=str, default=None)
    gen_parser.add_argument("--pexels-key", type=str, default=None)
    gen_parser.add_argument("--voice", type=str, default=None, help="TTS voice ID (default from config)")
    gen_parser.add_argument("--use-stock", action="store_true", help="Use Pexels stock photos")
    gen_parser.add_argument("--no-real", action="store_true", help="Skip real photos (DuckDuckGo)")
    gen_parser.add_argument("--no-validate", action="store_true", help="Skip Qwen VL image validation")
    gen_parser.add_argument("--assets-only", action="store_true", help="Generate assets only (no video assembly)")

    # scenario
    scen_parser = subparsers.add_parser("scenario", help="Generate scenario JSON")
    scen_parser.add_argument("topic", type=str, help="Video topic/theme")
    scen_parser.add_argument("--duration", type=int, default=30, help="Target duration (seconds)")
    scen_parser.add_argument("--style", type=str, default=None, help="Video style")
    scen_parser.add_argument("--language", type=str, default="en", help="Language")
    scen_parser.add_argument("--scenes", type=int, default=None, help="Number of scenes")
    scen_parser.add_argument("--output", "-o", type=str, default=None, help="Output JSON file")
    scen_parser.add_argument("--refine", "-r", type=str, default=None, help="Scenario file to refine")
    scen_parser.add_argument("--feedback", "-f", type=str, default=None, help="Feedback for refinement")
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


def _cmd_generate(args):
    from .core.video import VideoGeneratorV2

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
        voice_id=args.voice,
        use_real_photos=not args.no_real,
        use_stock_photos=args.use_stock,
        validate_images=not args.no_validate,
    )

    if args.assets_only:
        result = generator.generate_assets_only(
            topic=args.topic,
            language=args.language,
            duration=args.duration,
            style=args.style,
            num_scenes=args.scenes,
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
        )
        print(f"\nVideo ready: {result}")


def _cmd_scenario(args):
    from .core.scenario import VideoScenarioPlannerV2

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


if __name__ == "__main__":
    main()

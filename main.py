"""Main entry point for PyTTS Scraper."""

import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.planning.video_scenario_planner_v2 import VideoScenarioPlannerV2
from src.images.image_generator import ImageGenerator, WhiskAPI
from src.images.image_search import ImageSearch
from src.tts.tts_engine import tts
from src.video.video_generator_v2 import VideoGeneratorV2


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PyTTS Scraper - Automated video generation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a video from a topic
  python main.py generate "Space Exploration"

  # Generate video with custom settings
  python main.py generate "Cyberpunk City" --duration 60 --style cinematic

  # Generate only scenario
  python main.py scenario "History of Rome" --language en

  # Generate images only
  python main.py images "Forest landscape" --count 5

  # Generate TTS only
  python main.py tts "Hello world" --voice Elena
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Generate video command
    gen_parser = subparsers.add_parser("generate", help="Generate a complete video")
    gen_parser.add_argument("topic", type=str, help="Video topic/theme")
    gen_parser.add_argument("--duration", type=int, default=30, help="Target duration in seconds")
    gen_parser.add_argument("--style", type=str, default="documentary", help="Video style")
    gen_parser.add_argument("--language", type=str, default="en", help="Language (en, ru)")
    
    # Generate scenario command
    scen_parser = subparsers.add_parser("scenario", help="Generate video scenario")
    scen_parser.add_argument("topic", type=str, help="Video topic/theme")
    scen_parser.add_argument("--duration", type=int, default=30, help="Target duration")
    scen_parser.add_argument("--style", type=str, default="documentary", help="Video style")
    scen_parser.add_argument("--language", type=str, default="en", help="Language")
    
    # Generate images command
    img_parser = subparsers.add_parser("images", help="Generate images")
    img_parser.add_argument("prompt", type=str, help="Image description")
    img_parser.add_argument("--count", type=int, default=1, help="Number of images")
    img_parser.add_argument("--model", type=str, default="imagen3.5", help="Image model")
    img_parser.add_argument("--aspect", type=str, default="landscape", help="Aspect ratio")
    
    # Generate TTS command
    tts_parser = subparsers.add_parser("tts", help="Generate speech from text")
    tts_parser.add_argument("text", type=str, help="Text to synthesize")
    tts_parser.add_argument("--voice", type=str, default="Elena", help="Voice ID")
    tts_parser.add_argument("--output", type=str, default="output.wav", help="Output file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "generate":
        print(f"🎬 Generating video: {args.topic}")
        generator = VideoGeneratorV2(
            fireworks_api_key=os.environ.get("FIREWORKS_API_KEY"),
            whisk_cookie=os.environ.get("WHISK_COOKIE"),
            pexels_api_key=os.environ.get("PEXELS_API_KEY"),
            validate_images=True,
        )
        generator.generate_video(
            topic=args.topic,
            duration=args.duration,
            style=args.style,
            language=args.language,
        )
    
    elif args.command == "scenario":
        print(f"📝 Generating scenario: {args.topic}")
        planner = VideoScenarioPlannerV2(
            api_key=os.environ.get("FIREWORKS_API_KEY"),
        )
        scenario = planner.create_scenario(
            topic=args.topic,
            language=args.language,
            target_duration=args.duration,
            style=args.style,
        )
        print(f"✅ Scenario generated")
    
    elif args.command == "images":
        print(f"🎨 Generating images: {args.prompt}")
        generator = ImageGenerator(
            cookie=os.environ.get("WHISK_COOKIE", ""),
            output_dir="./image-output",
        )
        model = f"IMAGEN_{args.model.replace('imagen', '').replace('.', '_')}"
        aspect = f"IMAGE_ASPECT_RATIO_{args.aspect.upper()}"
        paths = generator.generate(
            prompt=args.prompt,
            model=model,
            aspect_ratio=aspect,
            count=args.count,
        )
        print(f"✅ Generated {len(paths)} images")
    
    elif args.command == "tts":
        print(f"🔊 Generating speech: {args.text}")
        success = tts(
            text=args.text,
            voice_id=args.voice,
            output_path=args.output,
        )
        if success:
            print(f"✅ Audio saved to {args.output}")
        else:
            print("❌ Failed to generate audio")
            sys.exit(1)


if __name__ == "__main__":
    main()

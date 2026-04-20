import os
import time

from .whisk import ImageGenerator
from ..core.llm import FireworksClient
from ..config import LLM_MODEL
from ..prompts import THUMBNAIL_PROMPT_TEMPLATE, THUMBNAIL_FALLBACK_TEMPLATE


class ThumbnailGenerator:
    def __init__(self, whisk_cookie: str, output_dir: str = "./thumbnails"):
        self.whisk_cookie = whisk_cookie
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_thumbnail(self, topic: str) -> str:
        prompt = self._create_clickbait_prompt(topic)

        print(f"\nGenerating clickbait thumbnail...")
        print(f"  Topic: {topic}")
        print(f"  Prompt: {prompt[:150]}...")

        generator = ImageGenerator(
            cookie=self.whisk_cookie,
            output_dir=self.output_dir
        )

        try:
            paths = generator.generate(
                prompt=prompt,
                model="IMAGEN_3_5",
                aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
                seed=0,
                count=1
            )

            if not paths:
                raise Exception("Failed to generate image")

            image_path = paths[0]
            timestamp = int(time.time())
            new_path = os.path.join(self.output_dir, f"thumbnail_{topic.replace(' ', '_')[:30]}_{timestamp}.png")
            if os.path.exists(image_path):
                os.rename(image_path, new_path)

            print(f"Thumbnail created: {new_path}\n")
            return new_path

        except Exception as e:
            error_msg = str(e)
            print(f"Thumbnail generation error: {error_msg}")
            
            if "400" in error_msg or "Bad Request" in error_msg:
                print(f"  Retrying with simplified prompt...")
                simplified_prompt = self._create_simplified_prompt(topic)
                try:
                    paths = generator.generate(
                        prompt=simplified_prompt,
                        model="IMAGEN_3_5",
                        aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
                        seed=0,
                        count=1
                    )
                    if paths:
                        image_path = paths[0]
                        timestamp = int(time.time())
                        new_path = os.path.join(self.output_dir, f"thumbnail_{topic.replace(' ', '_')[:30]}_{timestamp}.png")
                        if os.path.exists(image_path):
                            os.rename(image_path, new_path)
                        print(f"Thumbnail created (simplified): {new_path}\n")
                        return new_path
                except Exception as e2:
                    print(f"  Simplified prompt also failed: {e2}")
            
            print(f"  Creating fallback thumbnail...")
            return self._create_fallback_thumbnail(topic)
    
    def _create_simplified_prompt(self, topic: str) -> str:
        return f"Hyper-realistic 8k YouTube thumbnail, {topic}, dramatic lighting, high contrast, viral aesthetic, 4k"
    
    def _create_fallback_thumbnail(self, topic: str) -> str:
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new("RGB", (1920, 1080), (255, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 120)
        except:
            font = ImageFont.load_default()
        
        text = topic[:50]
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (1920 - text_w) // 2
        y = (1080 - text_h) // 2
        
        draw.text((x, y), text, fill="white", font=font)
        
        timestamp = int(time.time())
        fallback_path = os.path.join(self.output_dir, f"thumbnail_fallback_{timestamp}.png")
        img.save(fallback_path)
        
        print(f"Fallback thumbnail created: {fallback_path}")
        return fallback_path

    def _create_clickbait_prompt(self, topic: str) -> str:
        print(f"  Generating prompt via AI...")

        try:
            client = FireworksClient()
            prompt_request = THUMBNAIL_PROMPT_TEMPLATE.format(topic=topic)

            response = client.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt_request}],
                temperature=0.8,
                max_tokens=200,
                stream=False
            )

            llm_prompt = response.choices[0].message.content.strip()
            print(f"  AI prompt: {llm_prompt[:100]}...")
            return llm_prompt

        except Exception as e:
            print(f"  LLM error, using fallback: {e}")
            return THUMBNAIL_FALLBACK_TEMPLATE.format(topic=topic)

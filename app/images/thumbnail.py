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
            print(f"Thumbnail error: {e}")
            return None

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

"""
Генератор кликбейтных превью для видео на основе темы
Использует только Whisk API с правильными промптами - без добавления текста через PIL
"""

import os
import sys
from image_generator import ImageGenerator


class ThumbnailGenerator:
    """Генератор кликбейтных превью через AI"""
    
    def __init__(self, whisk_cookie: str, output_dir: str = "./thumbnails"):
        self.whisk_cookie = whisk_cookie
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_thumbnail(
        self,
        topic: str
    ) -> str:
        """
        Генерирует кликбейтное превью полностью через AI
        
        Args:
            topic: Тема видео
            
        Returns:
            Путь к превью
        """
        # Создаем супер-кликбейтный промпт на основе темы
        prompt = self._create_clickbait_prompt(topic)
        
        print(f"\n🎨 Генерация кликбейтного превью...")
        print(f"   Тема: {topic}")
        print(f"   Промпт: {prompt[:150]}...")
        
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
                raise Exception("Не удалось сгенерировать изображение")
            
            image_path = paths[0]
            
            # Переименовываем в thumbnail
            import time
            timestamp = int(time.time())
            new_path = os.path.join(self.output_dir, f"thumbnail_{topic.replace(' ', '_')[:30]}_{timestamp}.png")
            if os.path.exists(image_path):
                os.rename(image_path, new_path)
            
            print(f"✅ Превью создано: {new_path}\n")
            return new_path
            
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            return None
    
    def _create_clickbait_prompt(self, topic: str) -> str:
        """Создает промпт через LLM для идеального превью под тему"""
        from video_scenario_planner_v2 import VideoScenarioPlannerV2
        
        print(f"   🤖 Генерация промпта через AI...")
        
        # Создаем планировщик для запроса к LLM
        planner = VideoScenarioPlannerV2()
        
        # Запрос на создание промпта
        prompt_request = f"""
        Create a detailed image generation prompt for a YouTube thumbnail about: "{topic}"
        
        Requirements:
        - Eye-catching, viral-style thumbnail
        - Bold text overlay in Russian
        - High contrast, saturated colors
        - Professional 8k quality
        - MrBeast-style composition
        
        Return ONLY the image description prompt, no extra text.
        """
        
        try:
            # Получаем промпт от LLM
            response = planner.client.chat.completions.create(
                model="accounts/fireworks/models/qwen3p6-plus",
                messages=[{"role": "user", "content": prompt_request}],
                temperature=0.8,
                max_tokens=200,
                stream=False
            )
            
            llm_prompt = response.choices[0].message.content.strip()
            print(f"   ✅ AI промпт: {llm_prompt[:100]}...")
            
            return llm_prompt
            
        except Exception as e:
            print(f"   ⚠ Ошибка LLM, используем базовый промпт: {e}")
            return f"YouTube thumbnail about {topic}, viral style, bold text, 8k, high contrast"


def main():
    """CLI для генерации превью"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Генератор кликбейтных превью через AI")
    parser.add_argument("topic", help="Тема видео")
    parser.add_argument("--style", "-s", default="mystery",
                       choices=["mystery", "horror", "tech", "drama"],
                       help="Стиль превью")
    parser.add_argument("--whisk-cookie", help="Whisk cookie")
    
    args = parser.parse_args()
    
    # Получаем cookie
    cookie = args.whisk_cookie or os.environ.get("WHISK_COOKIE")
    if not cookie:
        print("❌ Укажите cookie через --whisk-cookie или WHISK_COOKIE")
        sys.exit(1)
    
    generator = ThumbnailGenerator(whisk_cookie=cookie)
    
    thumbnail_path = generator.generate_thumbnail(
        topic=args.topic,
        style=args.style
    )
    
    if thumbnail_path:
        print(f"🎉 Превью готово: {thumbnail_path}")
    else:
        print("❌ Не удалось создать превью")
        sys.exit(1)


if __name__ == "__main__":
    main()

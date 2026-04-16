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
        topic: str,
        style: str = "mystery"
    ) -> str:
        """
        Генерирует кликбейтное превью полностью через AI
        
        Args:
            topic: Тема видео
            style: Стиль (mystery, horror, tech, drama)
            
        Returns:
            Путь к превью
        """
        # Создаем супер-кликбейтный промпт
        prompt = self._create_clickbait_prompt(topic, style)
        
        print(f"\n🎨 Генерация кликбейтного превью...")
        print(f"   Тема: {topic}")
        print(f"   Стиль: {style}")
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
    
    def _create_clickbait_prompt(self, topic: str, style: str) -> str:
        """Создает идеальный кликбейтный промпт для AI"""
        
        prompts = {
            "mystery": f"""
            YouTube thumbnail for viral video about "{topic}".
            
            SHOCKING face of a person with wide eyes and open mouth in foreground, extreme close-up, dramatic reaction.
            
            Background: mysterious dark atmosphere with glowing question marks, red arrows pointing to hidden details, blurred conspiracy elements.
            
            Style: MrBeast thumbnail style, high contrast, saturated colors, dramatic rim lighting, bokeh effect.
            
            Text elements: Large bold red text "SHOCKING TRUTH!" in Impact font, yellow arrow, red circle highlighting mystery.
            
            Colors: Dark blue, purple, neon accents, high saturation.
            
            Professional YouTube thumbnail, 8k, hyper-detailed, eye-catching, viral content.
            """,
            
            "horror": f"""
            YouTube thumbnail for horror video about "{topic}".
            
            TERRIFIED screaming face in extreme close-up, sweat drops, pupils dilated, pure fear expression.
            
            Background: Dark foggy forest at night, shadowy monster silhouette with glowing red eyes, blood splatters, eerie green mist.
            
            Style: Horror movie poster, dramatic shadows, red emergency lighting, dutch angle, claustrophobic atmosphere.
            
            Text elements: Bold red dripping text "DON'T WATCH!", broken glass effect, warning symbols.
            
            Colors: Blood red, pitch black, sickly green, high contrast.
            
            Terrifying YouTube thumbnail, nightmare fuel, 8k, cinematic horror.
            """,
            
            "tech": f"""
            YouTube thumbnail for tech video about "{topic}".
            
            EXCITED person pointing at futuristic holographic display, mind-blown expression, finger pointing at camera.
            
            Background: Cyberpunk interface with glowing data streams, neon circuit boards, holographic graphs showing "1000% INCREASE", floating tech icons.
            
            Style: Modern tech reviewer thumbnail, neon glow, clean composition, futuristic UI elements.
            
            Text elements: Bold cyan text "GAME CHANGER!", glowing arrows, percentage numbers in green.
            
            Colors: Electric blue, cyan, magenta, bright accents, neon glow.
            
            Professional tech thumbnail, cyberpunk aesthetic, 8k, hyper-detailed.
            """,
            
            "drama": f"""
            YouTube thumbnail for dramatic video about "{topic}".
            
            EMOTIONAL person with tears or intense anger, dramatic facial expression, hands on head in disbelief.
            
            Background: Golden hour lighting, epic landscape, lens flare, cinematic bokeh, leading lines to subject.
            
            Style: Drama movie poster, emotional climax moment, rule of thirds, shallow depth of field.
            
            Text elements: Bold white text with black outline "LIFE CHANGING!", dramatic subtitle, emotional symbols.
            
            Colors: Warm orange, deep red, golden yellow, rich tones, high saturation.
            
            Epic dramatic thumbnail, emotional impact, 8k, cinematic photography.
            """
        }
        
        return prompts.get(style, prompts["mystery"]).strip()


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

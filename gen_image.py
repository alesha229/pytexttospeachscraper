"""
Генерация картинки через Whisk API.
Использование:
    python gen_image.py "Красивый закат"
    python gen_image.py "Cyberpunk city" --model imagen4 --aspect portrait
    python gen_image.py "Forest" --count 3 --all-aspects
    python gen_image.py "Logo" --aspects square,landscape
"""

import os
import sys
from src.images.image_generator import ImageGenerator, WhiskAPI, CONFIG, ASPECT_RATIOS, MODELS

ALL_ASPECTS = ["square", "portrait", "landscape"]


def main():
    if len(sys.argv) < 2:
        prompt = input("Промпт: ").strip()
        if not prompt:
            print("Пустой промпт")
            return
    else:
        prompt = sys.argv[1]

    model_key = "imagen3.5"
    aspect_keys = None
    count = 1
    seed = 0
    all_aspects = False

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--model", "-m") and i + 1 < len(sys.argv):
            model_key = sys.argv[i + 1]
            i += 2
        elif arg in ("--aspect", "-a") and i + 1 < len(sys.argv):
            aspect_keys = sys.argv[i + 1].split(",")
            i += 2
        elif arg in ("--all-aspects",):
            all_aspects = True
            i += 1
        elif arg in ("--count", "-c") and i + 1 < len(sys.argv):
            count = int(sys.argv[i + 1])
            i += 2
        elif arg in ("--seed", "-s") and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    cookie = os.environ.get("WHISK_COOKIE", CONFIG.get("cookie", ""))
    if not cookie:
        print("WHISK_COOKIE не задан")
        return

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image_gen")
    os.makedirs(output_dir, exist_ok=True)

    gen = ImageGenerator(cookie=cookie, output_dir=output_dir)

    model = MODELS.get(model_key, "IMAGEN_3_5")

    if all_aspects:
        aspects = ALL_ASPECTS
    elif aspect_keys:
        aspects = aspect_keys
    else:
        aspects = ["landscape"]

    print(f"Промпт: {prompt}")
    print(f"Модель: {model}, Форматы: {aspects}, Кол-во: {count}")

    for ak in aspects:
        aspect = ASPECT_RATIOS.get(ak.strip(), "IMAGE_ASPECT_RATIO_LANDSCAPE")
        print(f"\n▶ Генерация {ak} ({aspect})...")
        paths = gen.generate(prompt=prompt, model=model, aspect_ratio=aspect, seed=seed, count=count)
        if paths:
            for p in paths:
                print(f"  ✅ {p}")
        else:
            print(f"  ❌ Ошибка генерации {ak}")


if __name__ == "__main__":
    main()

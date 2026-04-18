"""
Консольный генератор изображений с использованием Whisk API (Google Labs)

Использование:
    python image_generator.py "Красивый закат" --cookie YOUR_COOKIE
    python image_generator.py "Cyberpunk city" --model imagen4 --aspect portrait
    python image_generator.py "Forest" --count 4 --seed 42

Вход:
    - prompt (str): Описание изображения (или через интерактивный ввод)
    - cookie (str): Cookie сессии Google (или через WHISK_COOKIE env)
    - model (str): Модель (imagen3, imagen3.5, imagen4)
    - aspect (str): Соотношение (square, portrait, landscape)
    - seed (int): Seed для воспроизводимости (0 = случайный)
    - count (int): Количество изображений (1-8)
    - dir (str): Папка вывода (по умолчанию ./output)

Выход:
    - PNG файлы в указанной папке (или ./output)
    - Имена файлов: generated_{timestamp}_{seed}_{index}.png

Доступные модели:
    - imagen3: IMAGEN_3
    - imagen3.5: IMAGEN_3_5 (по умолчанию)
    - imagen4: IMAGEN_4

Доступные соотношения:
    - square: 1:1
    - portrait: 9:16
    - landscape: 16:9 (по умолчанию)
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

# ============================================================
# ⚙️ КОНФИГУРАЦИЯ
# ============================================================
CONFIG = {
    "cookie": os.environ.get("WHISK_COOKIE", ""),
    "prompt": "крутой скелет играет на гитаре огонь",
    "output_dir": "./image-output",
    "model": "IMAGEN_3_5",
    "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    "seed": 0,
    "count": 1,
}
# ============================================================

# Маппинг коротких названий для удобства
ASPECT_RATIOS = {
    "square": "IMAGE_ASPECT_RATIO_SQUARE",
    "portrait": "IMAGE_ASPECT_RATIO_PORTRAIT",
    "landscape": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    "1:1": "IMAGE_ASPECT_RATIO_SQUARE",
    "9:16": "IMAGE_ASPECT_RATIO_PORTRAIT",
    "16:9": "IMAGE_ASPECT_RATIO_LANDSCAPE",
}

MODELS = {
    "imagen3": "IMAGEN_3",
    "imagen3.5": "IMAGEN_3_5",
    "imagen4": "IMAGEN_4",
    "3": "IMAGEN_3",
    "3.5": "IMAGEN_3_5",
    "4": "IMAGEN_4",
}


class WhiskAPI:
    """Клиент для работы с Whisk API"""
    
    AUTH_URL = "https://labs.google/fx/api/auth/session"
    TRPC_URL = "https://labs.google/fx/api/trpc"
    MEDIA_URL = "https://aisandbox-pa.googleapis.com/v1"
    MEDIA_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY"
    
    def __init__(self, cookie: str):
        """
        Инициализация клиента
        
        Args:
            cookie: Cookie сессии Google аккаунта
        """
        self.cookie = cookie
        self.auth_token = None
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self.session.cookies.set("__Secure-1PSID", cookie)
    
    def refresh_auth(self):
        """Обновление токена аутентификации"""
        try:
            response = self.session.get(
                self.AUTH_URL,
                headers={"cookie": f"__Secure-1PSID={self.cookie}"}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("error") == "ACCESS_TOKEN_REFRESH_NEEDED":
                raise Exception("Требуется новый cookie - сессия истекла")
            
            self.auth_token = data.get("access_token")
            if not self.auth_token:
                raise Exception(f"Не получен access_token. Ответ: {data}")
            
            return self.auth_token
        except Exception as e:
            raise Exception(f"Ошибка аутентификации: {e}")
    
    def _post(self, url: str, body: dict, use_auth_token: bool = False) -> dict:
        """Отправка POST запроса к API"""
        headers = {}
        if use_auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        else:
            headers["cookie"] = f"__Secure-1PSID={self.cookie}"
        
        response = self.session.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def create_project(self, name: str = "Console Generator") -> str:
        """
        Создание нового проекта (workflow)
        
        Args:
            name: Название проекта
            
        Returns:
            ID проекта (workflowId)
        """
        body = {
            "json": {
                "workflowMetadata": {
                    "workflowName": name
                }
            }
        }
        
        response = self._post(
            f"{self.TRPC_URL}/media.createOrUpdateWorkflow",
            body
        )
        return response["workflowId"]
    
    def generate_image(
        self,
        prompt: str,
        model: str = "IMAGEN_3_5",
        aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
        seed: int = 0,
        count: int = 1,
    ) -> list:
        """
        Генерация изображений
        
        Args:
            prompt: Текстовое описание изображения
            model: Модель генерации
            aspect_ratio: Соотношение сторон
            seed: Seed для воспроизводимости (0 = случайный)
            count: Количество изображений (1-8)
            
        Returns:
            Список объектов Media
        """
        # Валидация модели
        valid_models = ["IMAGEN_3", "IMAGEN_3_5", "IMAGEN_4"]
        if model not in valid_models:
            print(f"⚠ Неверная модель {model}, используем IMAGEN_3_5")
            model = "IMAGEN_3_5"
        
        # Валидация aspect_ratio
        valid_ratios = ["IMAGE_ASPECT_RATIO_SQUARE", "IMAGE_ASPECT_RATIO_PORTRAIT", "IMAGE_ASPECT_RATIO_LANDSCAPE"]
        if aspect_ratio not in valid_ratios:
            print(f"⚠ Неверный aspect_ratio {aspect_ratio}, используем IMAGE_ASPECT_RATIO_LANDSCAPE")
            aspect_ratio = "IMAGE_ASPECT_RATIO_LANDSCAPE"
        
        body = {
            "userInput": {
                "candidatesCount": count,
                "prompts": [prompt],
                "seed": seed
            },
            "clientContext": {
                "sessionId": f";{int(time.time() * 1000)}",
                "tool": "IMAGE_FX"
            },
            "modelInput": {
                "modelNameType": model
            },
            "aspectRatio": aspect_ratio
        }
        
        try:
            response = self._post(
                f"{self.MEDIA_URL}:runImageFx",
                body,
                use_auth_token=True
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"❌ Ошибка API (400 Bad Request): {e.response.text}")
                print(f"   Промпт: {prompt}")
                print(f"   Модель: {model}")
                print(f"   Aspect Ratio: {aspect_ratio}")
                print("   Попробуйте изменить промпт или использовать другую модель.")
            raise
        
        # Парсинг результатов
        images = []
        for panel in response.get("imagePanels", []):
            for img in panel.get("generatedImages", []):
                returned_ratio = img.get("aspectRatio", "")
                if returned_ratio and returned_ratio != aspect_ratio:
                    print(f"   ⚠ API вернул другой аспект: запрошен={aspect_ratio}, получен={returned_ratio}")
                images.append({
                    "seed": img.get("seed"),
                    "prompt": img.get("prompt"),
                    "workflowId": img.get("workflowId"),
                    "encoded_media": img.get("encodedImage"),
                    "media_generation_id": img.get("mediaGenerationId"),
                    "aspect_ratio": img.get("aspectRatio"),
                    "model": img.get("modelNameType"),
                })
        
        return images
    
    def download_image_from_base64(self, base64_data: str, save_path: str) -> str:
        """
        Сохранение изображения из base64
        
        Args:
            base64_data: Base64 encoded изображение
            save_path: Путь для сохранения
            
        Returns:
            Путь к сохранённому файлу
        """
        # Убираем data URI префикс если есть
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        
        image_bytes = base64.b64decode(base64_data)
        
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        
        return save_path
    
    def download_image_from_media_id(self, media_id: str, save_path: str) -> str:
        """
        Скачивание изображения по media ID
        
        Args:
            media_id: ID медиа
            save_path: Путь для сохранения
            
        Returns:
            Путь к сохранённому файлу
        """
        response = self.session.get(
            f"{self.MEDIA_URL}/media/{media_id}?key={self.MEDIA_KEY}",
            headers={
                "Referer": "https://labs.google/",
                "Authorization": f"Bearer {self.auth_token}",
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Извлечение encoded изображения
        media_info = data.get("image") or data.get("video")
        if not media_info:
            raise Exception("Не удалось получить данные изображения из ответа API")
        
        encoded_media = media_info.get("encodedImage") or media_info.get("encodedVideo")
        if not encoded_media:
            raise Exception("Encoded изображение отсутствует в ответе API")
        
        return self.download_image_from_base64(encoded_media, save_path)


class ImageGenerator:
    """Генератор изображений с сохранением в локальную папку"""
    
    def __init__(self, cookie: str, output_dir: str = "./output"):
        """
        Инициализация генератора
        
        Args:
            cookie: Cookie для аутентификации
            output_dir: Папка для сохранения изображений
        """
        self.api = WhiskAPI(cookie)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        prompt: str,
        model: str = "IMAGEN_3_5",
        aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
        seed: int = 0,
        count: int = 1,
    ) -> list:
        """
        Генерация и сохранение изображений
        
        Args:
            prompt: Текстовое описание
            model: Модель (IMAGEN_3, IMAGEN_3_5, IMAGEN_4)
            aspect_ratio: Соотношение сторон
            seed: Seed для воспроизводимости
            count: Количество изображений (1-8)
            
        Returns:
            Список путей к сохранённым файлам
        """
        print(f"🎨 Генерация изображений...")
        print(f"   Промпт: {prompt}")
        print(f"   Модель: {model}")
        print(f"   Соотношение: {aspect_ratio}")
        print(f"   Seed: {seed}")
        print(f"   Количество: {count}")
        
        # Аутентификация
        print(f"🔐 Аутентификация...")
        self.api.refresh_auth()
        print(f"   Успешно!")
        
        # Генерация изображений
        print(f"⏳ Генерация...")
        images = self.api.generate_image(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            seed=seed,
            count=count,
        )
        
        if not images:
            print(f"❌ Ошибка: изображения не сгенерированы")
            return []
        
        # Сохранение файлов
        saved_paths = []
        for i, img in enumerate(images, 1):
            timestamp = int(time.time())
            filename = f"generated_{timestamp}_{img['seed']}_{i}.png"
            filepath = self.output_dir / filename
            
            print(f"💾 Сохранение изображения {i}/{len(images)}...")
            self.api.download_image_from_base64(img["encoded_media"], filepath)
            
            if aspect_ratio != "IMAGE_ASPECT_RATIO_LANDSCAPE":
                filepath = self._crop_to_aspect(filepath, aspect_ratio)
            
            saved_paths.append(str(filepath))
            print(f"   ✅ {filepath}")
        
        return saved_paths

    def _crop_to_aspect(self, filepath: Path, target_ratio: str) -> Path:
        """Обрезает изображение до нужного соотношения сторон (центральный кроп)"""
        from PIL import Image as PILImage

        ratio_map = {
            "IMAGE_ASPECT_RATIO_SQUARE": 1.0,
            "IMAGE_ASPECT_RATIO_PORTRAIT": 9 / 16,
            "IMAGE_ASPECT_RATIO_LANDSCAPE": 16 / 9,
        }
        target = ratio_map.get(target_ratio)
        if not target:
            return filepath

        img = PILImage.open(filepath)
        w, h = img.size
        current = w / h

        if abs(current - target) < 0.01:
            return filepath

        if current > target:
            new_w = int(h * target)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        img.save(filepath)
        print(f"   ✂️ Обрезано до {target_ratio}: {img.size[0]}x{img.size[1]}")
        return filepath


def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Консольный генератор изображений через Whisk API (Google Labs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Базовая генерация
  python image_generator.py "Красивый закат на море" --cookie YOUR_COOKIE

  # С указанием модели и соотношения сторон
  python image_generator.py "Cyberpunk city" --model imagen4 --aspect portrait --cookie YOUR_COOKIE

  # С seed для воспроизводимости
  python image_generator.py "Cat astronaut" --seed 42 --cookie YOUR_COOKIE

  # Несколько изображений за раз
  python image_generator.py "Forest landscape" --count 4 --cookie YOUR_COOKIE

  # С указанием папки вывода
  python image_generator.py "Forest landscape" --dir ./my_images --cookie YOUR_COOKIE

Доступные модели: imagen3, imagen3.5, imagen4
Доступные соотношения: square (1:1), portrait (9:16), landscape (16:9)
        """,
    )
    
    parser.add_argument(
        "prompt",
        type=str,
        nargs="?",
        default=None,
        help="Текстовое описание изображения (если не указан, будет запрошен ввод)",
    )
    parser.add_argument(
        "--cookie", "-c",
        type=str,
        default=None,
        help="Cookie сессии Google аккаунта (или через переменную окружения WHISK_COOKIE)",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Модель генерации: imagen3, imagen3.5, imagen4 (по умолчанию: imagen3.5)",
    )
    parser.add_argument(
        "--aspect", "-a",
        type=str,
        default=None,
        help="Соотношение сторон: square, portrait, landscape (по умолчанию: landscape)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Seed для воспроизводимости (0 = случайный)",
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=None,
        help="Количество изображений для генерации (1-8)",
    )
    parser.add_argument(
        "--dir", "-d",
        type=str,
        default=None,
        help="Папка для сохранения изображений (по умолчанию: ./output)",
    )
    
    return parser.parse_args()


def main():
    """Точка входа"""
    args = parse_args()
    
    # Запрос промпта, если не указан
    prompt = args.prompt or CONFIG["prompt"]
    if not prompt:
        prompt = input("🎨 Введите описание изображения: ").strip()
        if not prompt:
            print("❌ Описание не может быть пустым")
            sys.exit(1)
    
    # Cookie: аргументы > CONFIG > окружение
    cookie = args.cookie or CONFIG["cookie"] or os.environ.get("WHISK_COOKIE")
    
    if not cookie:
        print("❌ Ошибка: не указан cookie!")
        print()
        print("Установите переменную окружения WHISK_COOKIE:")
        print("  PowerShell: $env:WHISK_COOKIE = 'your_cookie'")
        print("  CMD: set WHISK_COOKIE=your_cookie")
        print()
        print("Или укажите в CONFIG в начале файла image_generator.py")
        print("Или используйте флаг --cookie:")
        print("  python image_generator.py \"prompt\" --cookie your_cookie")
        sys.exit(1)
    
    # Нормализация параметров
    model_raw = args.model or CONFIG["model"]
    model = MODELS.get(model_raw.lower(), model_raw if model_raw.startswith("IMAGEN") else "IMAGEN_3_5")
    
    aspect_raw = args.aspect or CONFIG["aspect_ratio"]
    aspect_ratio = ASPECT_RATIOS.get(aspect_raw.lower(), aspect_raw if aspect_raw.startswith("IMAGE_ASPECT") else "IMAGE_ASPECT_RATIO_LANDSCAPE")
    
    seed = args.seed if args.seed is not None else CONFIG["seed"]
    count = args.count if args.count is not None else CONFIG["count"]
    output_dir = args.dir or CONFIG["output_dir"]
    
    # Создание генератора
    generator = ImageGenerator(
        cookie=cookie,
        output_dir=output_dir,
    )
    
    # Генерация изображений
    try:
        saved_paths = generator.generate(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            seed=seed,
            count=count,
        )
        
        if saved_paths:
            print()
            print(f"🎉 Изображения успешно созданы!")
            print(f"   Сохранено: {len(saved_paths)} файл(ов)")
            for path in saved_paths:
                print(f"   - {path}")
        else:
            print()
            print("❌ Не удалось создать изображения")
            sys.exit(1)
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ошибка: {e}")
        print("   Проверьте правильность cookie")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Ошибка соединения: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

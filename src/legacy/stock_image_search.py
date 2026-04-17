"""
Модуль для поиска бесплатных стоковых изображений
Поддерживает: Pexels, Unsplash, Pixabay (бесплатные API)

Использование:
    python stock_image_search.py "космос" --service pexels --count 5
    python stock_image_search.py "Илон Маск" --service unsplash --orientation landscape
    python stock_image_search.py "природа" --api-key YOUR_KEY --output ./images

Вход:
    - query (str): Поисковый запрос
    - service (str): Сервис (pexels, unsplash, pixabay)
    - api-key (str): API ключ (или через env переменные)
    - count (int): Количество изображений (по умолчанию 5)
    - orientation (str): Ориентация (landscape, portrait, square)
    - output (str): Папка для сохранения

Выход:
    - JSON с результатами поиска
    - Скачанные изображения в папке output
"""

import os
import sys
import json
import requests
from typing import List, Dict, Optional
from pathlib import Path
import time


# ============================================================
# ⚙️ КОНФИГУРАЦИЯ
# ============================================================
CONFIG = {
    "pexels_api_key": "",  # Pexels API key (или через PEXELS_API_KEY)
    "unsplash_api_key": "",  # Unsplash API key (или через UNSPLASH_API_KEY)
    "pixabay_api_key": "",  # Pixabay API key (или через PIXABAY_API_KEY)
    "output_dir": "./stock_images",
    "default_count": 5,
    "default_orientation": "landscape",
}
# ============================================================


class PexelsAPI:
    """Клиент для Pexels API (бесплатный, 200 запросов/час)"""
    
    BASE_URL = "https://api.pexels.com/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["pexels_api_key"] or os.environ.get("PEXELS_API_KEY")
        if not self.api_key:
            raise ValueError("Pexels API key не указан. Получите бесплатный ключ на https://www.pexels.com/api/")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.api_key,
            "User-Agent": "StockImageSearch/1.0"
        })
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
        """
        Поиск изображений
        
        Args:
            query: Поисковый запрос
            count: Количество результатов (1-80)
            orientation: Ориентация (landscape, portrait, square)
            
        Returns:
            Список словарей с информацией об изображениях
        """
        results = []
        page = 1
        per_page = min(count, 80)
        
        while len(results) < count:
            params = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "orientation": orientation,
            }
            
            response = self.session.get(f"{self.BASE_URL}/search", params=params)
            response.raise_for_status()
            
            data = response.json()
            photos = data.get("photos", [])
            
            if not photos:
                break
            
            for photo in photos:
                if len(results) >= count:
                    break
                
                results.append({
                    "id": str(photo["id"]),
                    "source": "pexels",
                    "url": photo["url"],
                    "photographer": photo.get("photographer", "Unknown"),
                    "photographer_url": photo.get("photographer_url", ""),
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "alt": photo.get("alt", ""),
                    "src": {
                        "original": photo["src"]["original"],
                        "large": photo["src"]["large"],
                        "medium": photo["src"]["medium"],
                        "small": photo["src"]["small"],
                        "tiny": photo["src"]["tiny"],
                    },
                    "download_url": photo["src"]["large"],  # Для скачивания
                })
            
            page += 1
            if len(photos) < per_page:
                break
        
        return results[:count]
    
    def download(self, photo_url: str, save_path: str) -> str:
        """Скачивает изображение по URL"""
        response = self.session.get(photo_url, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        return save_path


class UnsplashAPI:
    """Клиент для Unsplash API (бесплатный, 50 запросов/час)"""
    
    BASE_URL = "https://api.unsplash.com"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["unsplash_api_key"] or os.environ.get("UNSPLASH_API_KEY")
        if not self.api_key:
            raise ValueError("Unsplash API key не указан. Получите бесплатный ключ на https://unsplash.com/developers")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Client-ID {self.api_key}",
            "User-Agent": "StockImageSearch/1.0"
        })
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
        """
        Поиск изображений
        
        Args:
            query: Поисковый запрос
            count: Количество результатов (1-30)
            orientation: Ориентация (landscape, portrait, squarish)
            
        Returns:
            Список словарей с информацией об изображениях
        """
        results = []
        page = 1
        per_page = min(count, 30)
        
        while len(results) < count:
            params = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "orientation": orientation,
            }
            
            response = self.session.get(f"{self.BASE_URL}/search/photos", params=params)
            response.raise_for_status()
            
            data = response.json()
            photos = data.get("results", [])
            
            if not photos:
                break
            
            for photo in photos:
                if len(results) >= count:
                    break
                
                results.append({
                    "id": photo["id"],
                    "source": "unsplash",
                    "url": photo["links"]["html"],
                    "photographer": photo["user"]["name"],
                    "photographer_url": photo["user"]["links"]["html"],
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "alt": photo.get("alt_description", ""),
                    "src": {
                        "original": photo["urls"]["full"],
                        "large": photo["urls"]["regular"],
                        "medium": photo["urls"]["small"],
                        "small": photo["urls"]["thumb"],
                    },
                    "download_url": photo["urls"]["regular"],
                    "download_location": photo["links"]["download_location"],
                })
            
            page += 1
            if len(photos) < per_page:
                break
        
        return results[:count]
    
    def download(self, photo_url: str, save_path: str) -> str:
        """Скачивает изображение по URL"""
        response = self.session.get(photo_url, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        return save_path


class PixabayAPI:
    """Клиент для Pixabay API (бесплатный, 5000 запросов/час)"""
    
    BASE_URL = "https://pixabay.com/api"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["pixabay_api_key"] or os.environ.get("PIXABAY_API_KEY")
        if not self.api_key:
            raise ValueError("Pixabay API key не указан. Получите бесплатный ключ на https://pixabay.com/api/docs/")
        
        self.session = requests.Session()
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
        """
        Поиск изображений
        
        Args:
            query: Поисковый запрос
            count: Количество результатов (1-500)
            orientation: Ориентация (all, horizontal, vertical)
            
        Returns:
            Список словарей с информацией об изображениях
        """
        results = []
        page = 1
        per_page = min(count, 200)
        
        # Конвертация orientation
        orientation_map = {
            "landscape": "horizontal",
            "portrait": "vertical",
            "square": "all",
        }
        pixabay_orientation = orientation_map.get(orientation, "horizontal")
        
        while len(results) < count:
            params = {
                "key": self.api_key,
                "q": query,
                "page": page,
                "per_page": per_page,
                "orientation": pixabay_orientation,
                "image_type": "photo",
            }
            
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            hits = data.get("hits", [])
            
            if not hits:
                break
            
            for hit in hits:
                if len(results) >= count:
                    break
                
                results.append({
                    "id": str(hit["id"]),
                    "source": "pixabay",
                    "url": hit["pageURL"],
                    "photographer": hit.get("user", "Unknown"),
                    "photographer_url": hit.get("userImageURL", ""),
                    "width": hit.get("imageWidth", 0),
                    "height": hit.get("imageHeight", 0),
                    "alt": hit.get("tags", ""),
                    "src": {
                        "original": hit.get("largeImageURL", hit["webformatURL"]),
                        "large": hit.get("largeImageURL", hit["webformatURL"]),
                        "medium": hit["webformatURL"],
                        "small": hit.get("previewURL", ""),
                    },
                    "download_url": hit.get("largeImageURL", hit["webformatURL"]),
                })
            
            page += 1
            if len(hits) < per_page:
                break
        
        return results[:count]
    
    def download(self, photo_url: str, save_path: str) -> str:
        """Скачивает изображение по URL"""
        response = self.session.get(photo_url, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        return save_path


class StockImageSearch:
    """Универсальный поисковик стоковых изображений"""
    
    def __init__(
        self,
        pexels_key: str = None,
        unsplash_key: str = None,
        pixabay_key: str = None,
        output_dir: str = None
    ):
        self.output_dir = Path(output_dir or CONFIG["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.services = {}
        
        if pexels_key or CONFIG["pexels_api_key"] or os.environ.get("PEXELS_API_KEY"):
            self.services["pexels"] = PexelsAPI(pexels_key)
        
        if unsplash_key or CONFIG["unsplash_api_key"] or os.environ.get("UNSPLASH_API_KEY"):
            self.services["unsplash"] = UnsplashAPI(unsplash_key)
        
        if pixabay_key or CONFIG["pixabay_api_key"] or os.environ.get("PIXABAY_API_KEY"):
            self.services["pixabay"] = PixabayAPI(pixabay_key)
    
    def search(
        self,
        query: str,
        service: str = "pexels",
        count: int = 5,
        orientation: str = "landscape",
        save: bool = False
    ) -> List[Dict]:
        """
        Поиск изображений
        
        Args:
            query: Поисковый запрос
            service: Сервис (pexels, unsplash, pixabay)
            count: Количество результатов
            orientation: Ориентация
            save: Сохранять ли изображения
            
        Returns:
            Список результатов
        """
        if service not in self.services:
            raise ValueError(f"Сервис '{service}' не настроен. Доступные: {list(self.services.keys())}")
        
        print(f"🔍 Поиск: '{query}' в {service} ({count} шт, {orientation})")
        
        api = self.services[service]
        results = api.search(query, count, orientation)
        
        print(f"   ✅ Найдено: {len(results)} изображений")
        
        if save:
            print(f"   💾 Скачивание...")
            for i, result in enumerate(results, 1):
                filename = f"{service}_{result['id']}_{i}.jpg"
                save_path = self.output_dir / filename
                
                try:
                    api.download(result["download_url"], save_path)
                    result["local_path"] = str(save_path)
                    print(f"      ✅ {filename}")
                    time.sleep(0.5)  # Пауза между скачиваниями
                except Exception as e:
                    print(f"      ❌ Ошибка скачивания: {e}")
        
        return results
    
    def search_person(self, name: str, service: str = "pexels", count: int = 3) -> List[Dict]:
        """
        Поиск фото персоны
        
        Args:
            name: Имя человека
            service: Сервис
            count: Количество результатов
            
        Returns:
            Список результатов
        """
        print(f"👤 Поиск фото персоны: {name}")
        return self.search(name, service, count, "portrait")
    
    def search_location(self, name: str, service: str = "pexels", count: int = 3) -> List[Dict]:
        """
        Поиск фото локации
        
        Args:
            name: Название локации
            service: Сервис
            count: Количество результатов
            
        Returns:
            Список результатов
        """
        print(f"📍 Поиск фото локации: {name}")
        return self.search(name, service, count, "landscape")
    
    def search_object(self, name: str, service: str = "pexels", count: int = 3) -> List[Dict]:
        """
        Поиск фото объекта
        
        Args:
            name: Название объекта
            service: Сервис
            count: Количество результатов
            
        Returns:
            Список результатов
        """
        print(f"🎯 Поиск фото объекта: {name}")
        return self.search(name, service, count, "landscape")
    
    def save_results_json(self, results: List[Dict], filepath: str):
        """Сохраняет результаты поиска в JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ Результаты сохранены: {filepath}")


def cli():
    """CLI интерфейс"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Поиск бесплатных стоковых изображений",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python stock_image_search.py "космос" --service pexels --count 5
  python stock_image_search.py "Илон Маск" --service unsplash --orientation portrait
  python stock_image_search.py "природа" --api-key YOUR_KEY --output ./images --save
  python stock_image_search.py "лес" --service pixabay --count 10 --save
        """
    )
    
    parser.add_argument("query", help="Поисковый запрос")
    parser.add_argument("--service", "-s", default="pexels", 
                       choices=["pexels", "unsplash", "pixabay"],
                       help="Сервис поиска (по умолчанию: pexels)")
    parser.add_argument("--api-key", "-k", help="API ключ (или через env переменную)")
    parser.add_argument("--count", "-n", type=int, default=CONFIG["default_count"],
                       help=f"Количество изображений (по умолчанию: {CONFIG['default_count']})")
    parser.add_argument("--orientation", "-o", default=CONFIG["default_orientation"],
                       choices=["landscape", "portrait", "square"],
                       help=f"Ориентация (по умолчанию: {CONFIG['default_orientation']})")
    parser.add_argument("--output", "-d", help=f"Папка для сохранения (по умолчанию: {CONFIG['output_dir']})")
    parser.add_argument("--save", action="store_true", help="Скачать изображения")
    parser.add_argument("--json", action="store_true", help="Сохранить результаты в JSON")
    
    args = parser.parse_args()
    
    # API ключ
    api_key = args.api_key
    env_var_map = {
        "pexels": "PEXELS_API_KEY",
        "unsplash": "UNSPLASH_API_KEY",
        "pixabay": "PIXABAY_API_KEY",
    }
    
    if not api_key:
        api_key = os.environ.get(env_var_map.get(args.service, ""))
    
    if not api_key and args.service in ["pexels", "unsplash", "pixabay"]:
        print(f"⚠ API ключ для {args.service} не указан!")
        print(f"   Установите env: ${env_var_map.get(args.service, '')}")
        print(f"   Или используйте --api-key")
        print(f"   Получите ключ на https://www.{args.service}.com/api/")
        sys.exit(1)
    
    # Создание поисковика
    kwargs = {f"{args.service}_key": api_key}
    searcher = StockImageSearch(
        output_dir=args.output,
        **kwargs
    )
    
    # Поиск
    results = searcher.search(
        query=args.query,
        service=args.service,
        count=args.count,
        orientation=args.orientation,
        save=args.save
    )
    
    # Вывод результатов
    if results:
        print(f"\n🎉 Найдено {len(results)} изображений:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.get('alt', 'No description')[:80]}")
            print(f"     Фотограф: {r.get('photographer', 'Unknown')}")
            print(f"     URL: {r.get('url', '')[:80]}")
            if "local_path" in r:
                print(f"     Файл: {r['local_path']}")
            print()
        
        # Сохранение JSON
        if args.json:
            json_path = os.path.join(
                args.output or CONFIG["output_dir"],
                f"search_{args.query.replace(' ', '_')}.json"
            )
            searcher.save_results_json(results, json_path)
    else:
        print("❌ Ничего не найдено")
        sys.exit(1)


if __name__ == "__main__":
    cli()

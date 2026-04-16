"""
Модуль для поиска изображений из нескольких источников:
1. Стоковые фото (Pexels, Unsplash, Pixabay)
2. Реальные фото/скриншоты через SerpAPI (Google Images)

Использование:
    python image_search.py "космос" --source stock --count 5
    python image_search.py "Илон Маск" --source real --count 3
    python image_search.py "скриншот youtube" --source real --api-key YOUR_KEY

Вход:
    - query (str): Поисковый запрос
    - source (str): Источник (stock, real, both)
    - api-key (str): API ключи (или через env переменные)
    - count (int): Количество изображений
    - orientation (str): Ориентация
    - output (str): Папка для сохранения

Выход:
    - JSON с результатами поиска
    - Скачанные изображения
"""

from ddgs import DDGS
import requests
from typing import List, Dict, Optional
from pathlib import Path
import time
import os
import sys
import json


# ============================================================
# ⚙️ КОНФИГУРАЦИЯ
# ============================================================
CONFIG = {
    "pexels_api_key": "",
    "unsplash_api_key": "",
    "pixabay_api_key": "",
    "output_dir": "./search_results",
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
            raise ValueError("Pexels API key не указан")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.api_key,
            "User-Agent": "ImageSearch/1.0"
        })
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
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
                    "source_type": "stock",
                    "url": photo["url"],
                    "photographer": photo.get("photographer", "Unknown"),
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "alt": photo.get("alt", ""),
                    "src": {
                        "original": photo["src"]["original"],
                        "large": photo["src"]["large"],
                        "medium": photo["src"]["medium"],
                        "small": photo["src"]["small"],
                    },
                    "download_url": photo["src"]["large"],
                })
            
            page += 1
            if len(photos) < per_page:
                break
        
        return results[:count]
    
    def download(self, photo_url: str, save_path: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.pexels.com/"
        }
        response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        return save_path


class UnsplashAPI:
    """Клиент для Unsplash API"""
    
    BASE_URL = "https://api.unsplash.com"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["unsplash_api_key"] or os.environ.get("UNSPLASH_API_KEY")
        if not self.api_key:
            raise ValueError("Unsplash API key не указан")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Client-ID {self.api_key}",
            "User-Agent": "ImageSearch/1.0"
        })
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
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
                    "source_type": "stock",
                    "url": photo["links"]["html"],
                    "photographer": photo["user"]["name"],
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
                })
            
            page += 1
            if len(photos) < per_page:
                break
        
        return results[:count]
    
    def download(self, photo_url: str, save_path: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://unsplash.com/"
        }
        response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        return save_path


class PixabayAPI:
    """Клиент для Pixabay API"""
    
    BASE_URL = "https://pixabay.com/api"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["pixabay_api_key"] or os.environ.get("PIXABAY_API_KEY")
        if not self.api_key:
            raise ValueError("Pixabay API key не указан")
        
        self.session = requests.Session()
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
        results = []
        page = 1
        per_page = min(count, 200)
        
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
                    "source_type": "stock",
                    "url": hit["pageURL"],
                    "photographer": hit.get("user", "Unknown"),
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://pixabay.com/"
        }
        response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        return save_path


class DuckDuckGoImageSearch:
    """Клиент для поиска изображений через DuckDuckGo (бесплатно, без ключей)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        })
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
        """
        Поиск изображений через DuckDuckGo с повторными попытками при rate limit
        """
        results = []
        max_retries = 3
        retry_delay = 2  # секунды
        
        for attempt in range(max_retries):
            try:
                with DDGS() as ddgs:
                    ddgs_results = list(ddgs.images(
                        query,  # Используем позиционный аргумент
                        region='wt-wt',
                        safesearch='off',
                        max_results=min(count, 10)
                    ))
                    
                    if not ddgs_results:
                        return []
                    
                    for img in ddgs_results[:count]:
                        results.append({
                            "id": str(hash(img.get("image", ""))),
                            "source": "duckduckgo",
                            "source_type": "real",
                            "url": img.get("url", ""),
                            "photographer": img.get("source", "Unknown"),
                            "width": 0,
                            "height": 0,
                            "alt": img.get("title", ""),
                            "src": {
                                "original": img.get("image", ""),
                                "large": img.get("image", ""),
                                "medium": img.get("thumbnail", ""),
                                "small": img.get("thumbnail", ""),
                            },
                            "download_url": img.get("image", ""),
                            "is_real": True,
                        })
                    
                    return results
                    
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "Ratelimit" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"   ⏳ Rate limit DuckDuckGo. Повторная попытка через {wait_time}с...")
                        time.sleep(wait_time)
                    else:
                        print(f"   ⚠ DuckDuckGo rate limit. Пропускаем поиск, используем генерацию.")
                        return []
                else:
                    print(f"   ⚠ Ошибка DuckDuckGo поиска: {e}")
                    return []
        
        return results
    
    def download(self, photo_url: str, save_path: str) -> str:
        """Скачивает изображение по URL с эмуляцией браузера"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/"
            }
            response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            
            return save_path
        except Exception as e:
            print(f"   ⚠ Ошибка скачивания: {e}")
            raise


class BingImageSearchAPI:
    """Клиент для поиска реальных фото/скриншотов через Bing Image Search API"""
    
    BASE_URL = "https://api.bing.microsoft.com/v7.0/images/search"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG.get("bing_api_key") or os.environ.get("BING_API_KEY")
        if not self.api_key:
            raise ValueError("Bing API key не указан. Получите бесплатный ключ на https://www.microsoft.com/en-us/bing/apis/bing-image-search-api")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Ocp-Apim-Subscription-Key": self.api_key,
            "User-Agent": "ImageSearch/1.0"
        })
    
    def search(self, query: str, count: int = 5, orientation: str = "landscape") -> List[Dict]:
        """
        Поиск реальных фото и скриншотов через Bing Image Search
        
        Args:
            query: Поисковый запрос
            count: Количество результатов
            orientation: Ориентация (landscape, portrait, square)
            
        Returns:
            Список словарей с информацией об изображениях
        """
        results = []
        
        params = {
            "q": query,
            "count": min(count, 50),
            "imageType": "Photo",
        }
        
        if orientation == "landscape":
            params["aspect"] = "Wide"
        elif orientation == "portrait":
            params["aspect"] = "Tall"
        elif orientation == "square":
            params["aspect"] = "Square"
        
        try:
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            images = data.get("value", [])
            
            if not images:
                return []
            
            for img in images[:count]:
                results.append({
                    "id": img.get("imageId", str(hash(img.get("contentUrl", "")))),
                    "source": "bing",
                    "source_type": "real",
                    "url": img.get("contentUrl", ""),
                    "photographer": img.get("creator", {}).get("name", "Unknown") if isinstance(img.get("creator"), dict) else "Unknown",
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                    "alt": img.get("name", ""),
                    "src": {
                        "original": img.get("contentUrl", ""),
                        "large": img.get("contentUrl", ""),
                        "medium": img.get("thumbnailUrl", ""),
                        "small": img.get("thumbnailUrl", ""),
                    },
                    "download_url": img.get("contentUrl", ""),
                    "is_real": True,
                })
            
        except Exception as e:
            print(f"   ⚠ Ошибка Bing API: {e}")
            return []
        
        return results
    
    def download(self, photo_url: str, save_path: str) -> str:
        """Скачивает изображение по URL с эмуляцией браузера"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.bing.com/"
            }
            response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            
            return save_path
        except Exception as e:
            print(f"   ⚠ Ошибка скачивания: {e}")
            raise


class ImageSearch:
    """Универсальный поисковик изображений (сток + реальные фото)"""
    
    def __init__(
        self,
        pexels_key: str = None,
        unsplash_key: str = None,
        pixabay_key: str = None,
        bing_key: str = None,
        use_duckduckgo: bool = True,
        output_dir: str = None
    ):
        self.output_dir = Path(output_dir or CONFIG["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.services = {}
        
        # Стоковые сервисы
        if pexels_key or CONFIG["pexels_api_key"] or os.environ.get("PEXELS_API_KEY"):
            self.services["pexels"] = PexelsAPI(pexels_key)
        
        if unsplash_key or CONFIG["unsplash_api_key"] or os.environ.get("UNSPLASH_API_KEY"):
            self.services["unsplash"] = UnsplashAPI(unsplash_key)
        
        if pixabay_key or CONFIG["pixabay_api_key"] or os.environ.get("PIXABAY_API_KEY"):
            self.services["pixabay"] = PixabayAPI(pixabay_key)
        
        # Реальные фото/скриншоты
        if use_duckduckgo:
            self.services["real"] = DuckDuckGoImageSearch()
        elif bing_key or CONFIG.get("bing_api_key") or os.environ.get("BING_API_KEY"):
            self.services["real"] = BingImageSearchAPI(bing_key)
    
    def search(
        self,
        query: str,
        source: str = "stock",
        stock_service: str = "pexels",
        count: int = 5,
        orientation: str = "landscape",
        save: bool = False
    ) -> List[Dict]:
        """
        Поиск изображений
        
        Args:
            query: Поисковый запрос
            source: Источник (stock, real, both)
            stock_service: Сервис стока (pexels, unsplash, pixabay)
            count: Количество результатов
            orientation: Ориентация
            save: Сохранять ли изображения
            
        Returns:
            Список результатов
        """
        all_results = []
        
        if source in ["stock", "both"]:
            if stock_service not in self.services:
                raise ValueError(f"Сервис '{stock_service}' не настроен")
            
            print(f"🔍 Поиск стоковых: '{query}' в {stock_service}")
            api = self.services[stock_service]
            stock_results = api.search(query, count, orientation)
            print(f"   ✅ Найдено: {len(stock_results)} стоковых изображений")
            all_results.extend(stock_results)
        
        if source in ["real", "both"]:
            if "real" not in self.services:
                print("   ⚠ Bing API не настроен. Пропускаем поиск реальных фото.")
            else:
                print(f"🔍 Поиск реальных фото/скриншотов: '{query}'")
                api = self.services["real"]
                real_results = api.search(query, count, orientation)
                print(f"   ✅ Найдено: {len(real_results)} реальных фото")
                all_results.extend(real_results)
        
        # Скачивание если нужно
        if save:
            print(f"   💾 Скачивание...")
            for i, result in enumerate(all_results, 1):
                source_type = result.get("source_type", "unknown")
                filename = f"{result['source']}_{result['id']}_{i}.jpg"
                save_path = self.output_dir / filename
                
                try:
                    if source_type == "stock":
                        api = self.services.get(stock_service)
                    else:
                        api = self.services.get("real")
                    
                    if api:
                        api.download(result["download_url"], save_path)
                        result["local_path"] = str(save_path)
                        print(f"      ✅ {filename}")
                        time.sleep(0.5)
                except Exception as e:
                    print(f"      ❌ Ошибка скачивания: {e}")
        
        return all_results
    
    def search_person(self, name: str, source: str = "real", count: int = 3) -> List[Dict]:
        """Поиск фото персоны (реальные фото приоритетнее)"""
        print(f"👤 Поиск фото персоны: {name}")
        return self.search(name, source=source, count=count, orientation="portrait")
    
    def search_location(self, name: str, source: str = "stock", count: int = 3) -> List[Dict]:
        """Поиск фото локации"""
        print(f"📍 Поиск фото локации: {name}")
        return self.search(name, source=source, count=count, orientation="landscape")
    
    def search_object(self, name: str, source: str = "both", count: int = 3) -> List[Dict]:
        """Поиск фото объекта"""
        print(f"🎯 Поиск фото объекта: {name}")
        return self.search(name, source=source, count=count, orientation="landscape")
    
    def search_screenshot(self, query: str, count: int = 3) -> List[Dict]:
        """Поиск скриншотов (только реальные фото)"""
        print(f"📸 Поиск скриншотов: {query}")
        return self.search(query, source="real", count=count)
    
    def save_results_json(self, results: List[Dict], filepath: str):
        """Сохраняет результаты поиска в JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ Результаты сохранены: {filepath}")


def cli():
    """CLI интерфейс"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Поиск изображений (сток + реальные фото/скриншоты)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Только стоковые фото
  python image_search.py "космос" --source stock --stock-service pexels --count 5
  
  # Только реальные фото/скриншоты
  python image_search.py "Илон Маск" --source real --count 3
  
  # Оба источника
  python image_search.py "красная машина" --source both --count 10
  
  # Поиск скриншотов
  python image_search.py "youtube интерфейс" --source real --count 5
  
  # С сохранением
  python image_search.py "природа" --source stock --save --output ./images
        """
    )
    
    parser.add_argument("query", help="Поисковый запрос")
    parser.add_argument("--source", "-s", default="stock", 
                       choices=["stock", "real", "both"],
                       help="Источник изображений (по умолчанию: stock)")
    parser.add_argument("--stock-service", default="pexels",
                       choices=["pexels", "unsplash", "pixabay"],
                       help="Сервис стока (по умолчанию: pexels)")
    parser.add_argument("--api-key", "-k", help="API ключ (или через env)")
    parser.add_argument("--count", "-n", type=int, default=CONFIG["default_count"],
                       help=f"Количество изображений (по умолчанию: {CONFIG['default_count']})")
    parser.add_argument("--orientation", "-o", default=CONFIG["default_orientation"],
                       choices=["landscape", "portrait", "square"],
                       help=f"Ориентация (по умолчанию: {CONFIG['default_orientation']})")
    parser.add_argument("--output", "-d", help=f"Папка для сохранения")
    parser.add_argument("--save", action="store_true", help="Скачать изображения")
    parser.add_argument("--json", action="store_true", help="Сохранить JSON")
    
    args = parser.parse_args()
    
    # API ключи из env
    pexels_key = args.api_key if args.stock_service == "pexels" else os.environ.get("PEXELS_API_KEY")
    unsplash_key = args.api_key if args.stock_service == "unsplash" else os.environ.get("UNSPLASH_API_KEY")
    pixabay_key = args.api_key if args.stock_service == "pixabay" else os.environ.get("PIXABAY_API_KEY")
    serpapi_key = args.api_key or os.environ.get("SERPAPI_KEY")
    
    # Проверка ключей
    if args.source in ["stock", "both"]:
        key_map = {
            "pexels": pexels_key or os.environ.get("PEXELS_API_KEY"),
            "unsplash": unsplash_key or os.environ.get("UNSPLASH_API_KEY"),
            "pixabay": pixabay_key or os.environ.get("PIXABAY_API_KEY"),
        }
        if not key_map.get(args.stock_service):
            print(f"⚠ API ключ для {args.stock_service} не указан!")
            print(f"   Получите ключ на https://www.{args.stock_service}.com/api/")
            sys.exit(1)
    
    if args.source in ["real", "both"] and not serpapi_key:
        print("⚠ SerpAPI key не указан! Поиск реальных фото будет пропущен.")
        print("   Получите ключ на https://serpapi.com/ (бесплатно 100 запросов/месяц)")
    
    # Создание поисковика
    kwargs = {
        "pexels_key": pexels_key,
        "unsplash_key": unsplash_key,
        "pixabay_key": pixabay_key,
        "serpapi_key": serpapi_key,
    }
    searcher = ImageSearch(output_dir=args.output, **kwargs)
    
    # Поиск
    results = searcher.search(
        query=args.query,
        source=args.source,
        stock_service=args.stock_service,
        count=args.count,
        orientation=args.orientation,
        save=args.save
    )
    
    # Вывод
    if results:
        print(f"\n🎉 Найдено {len(results)} изображений:")
        for i, r in enumerate(results, 1):
            source_type = r.get("source_type", "unknown")
            print(f"  {i}. [{source_type.upper()}] {r.get('alt', 'No description')[:80]}")
            print(f"     Источник: {r.get('source', 'Unknown')}")
            print(f"     URL: {r.get('url', '')[:80]}")
            if "local_path" in r:
                print(f"     Файл: {r['local_path']}")
            print()
        
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

from ddgs import DDGS as DDGSearch
import requests
from typing import List, Dict, Optional
from pathlib import Path
import time
import os
import sys
import json

from ..config import PEXELS_API_KEY, UNSPLASH_API_KEY, PIXABAY_API_KEY, BING_API_KEY, EXA_API_KEY, TAVILY_API_KEY, SEARCH_RESULTS_DIR


class PexelsAPI:
    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or PEXELS_API_KEY
        if not self.api_key:
            raise ValueError("Pexels API key not set")
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
            params = {"query": query, "page": page, "per_page": per_page, "orientation": orientation}
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
                    "id": str(photo["id"]), "source": "pexels", "source_type": "stock",
                    "url": photo["url"], "photographer": photo.get("photographer", "Unknown"),
                    "width": photo.get("width", 0), "height": photo.get("height", 0),
                    "alt": photo.get("alt", ""),
                    "src": {"original": photo["src"]["original"], "large": photo["src"]["large"],
                            "medium": photo["src"]["medium"], "small": photo["src"]["small"]},
                    "download_url": photo["src"]["large"],
                })
            page += 1
            if len(photos) < per_page:
                break
        return results[:count]

    def download(self, photo_url: str, save_path: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.pexels.com/"}
        response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        return save_path


class DuckDuckGoImageSearch:
    def __init__(self, validator=None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.google.com/"
        })
        self.validator = validator

    def search(self, query: str, count: int = 5, orientation: str = "landscape",
               validate: bool = None, video_theme: str = "") -> List[Dict]:
        use_validation = validate if validate is not None else bool(self.validator)
        if use_validation and not self.validator:
            use_validation = False
        max_retries = 3
        retry_delay = 2

        if use_validation:
            return self._search_with_validation(query, count, max_retries, retry_delay, video_theme)

        results = []
        for attempt in range(max_retries):
            try:
                with DDGSearch() as ddgs:
                    ddgs_results = list(ddgs.images(query, region='wt-wt', safesearch='off', max_results=min(count, 10)))
                    if not ddgs_results:
                        return []
                    for img in ddgs_results[:count]:
                        results.append({
                            "id": str(hash(img.get("image", ""))), "source": "duckduckgo",
                            "source_type": "real", "url": img.get("url", ""),
                            "photographer": img.get("source", "Unknown"),
                            "width": 0, "height": 0, "alt": img.get("title", ""),
                            "src": {"original": img.get("image", ""), "large": img.get("image", ""),
                                    "medium": img.get("thumbnail", ""), "small": img.get("thumbnail", "")},
                            "download_url": img.get("image", ""), "is_real": True,
                        })
                    return results
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "Ratelimit" in error_msg:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        return []
                else:
                    return []
        return results

    def _search_with_validation(self, query, count, max_retries, retry_delay, video_theme=""):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        validated_results = []
        style_mismatch_results = []
        fallback_results = []
        all_seen_urls = set()
        attempts = 0
        max_total = count * 4
        consecutive_empty_batches = 0
        max_workers = 3

        while len(validated_results) < count and attempts < max_total:
            batch_size = min(count - len(validated_results) + max_workers + 2, 10)
            attempts += batch_size

            ddgs_results = []
            for attempt in range(max_retries):
                try:
                    with DDGSearch() as ddgs:
                        ddgs_results = list(ddgs.images(query, region='wt-wt', safesearch='off', max_results=batch_size))
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        break

            if not ddgs_results:
                break

            new_images = [img for img in ddgs_results if img.get("image", "") and img.get("image", "") not in all_seen_urls]
            for img in new_images:
                all_seen_urls.add(img.get("image", ""))

            if not new_images:
                consecutive_empty_batches += 1
                if consecutive_empty_batches >= 2:
                    break
                time.sleep(3)
                continue
            else:
                consecutive_empty_batches = 0

            def _validate_one(img):
                image_url = img.get("image", "")
                validation = self.validator.validate(image_url=image_url, query=query, video_theme=video_theme or None)
                is_match = validation["match"] and validation["confidence"] >= self.validator.confidence_threshold
                style_ok = validation.get("style_match", True) and validation.get("style_confidence", 0) >= self.validator.style_confidence_threshold
                return img, validation, is_match, style_ok

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_validate_one, img): img for img in new_images}
                for future in as_completed(futures):
                    if len(validated_results) >= count:
                        pool.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        img, validation, is_match, style_ok = future.result()
                    except Exception:
                        continue
                    image_url = img.get("image", "")
                    if is_match and style_ok:
                        validated_results.append({
                            "id": str(hash(image_url)), "source": "duckduckgo",
                            "source_type": "real", "url": img.get("url", ""),
                            "photographer": img.get("source", "Unknown"),
                            "width": 0, "height": 0, "alt": img.get("title", ""),
                            "src": {"original": image_url, "large": image_url,
                                    "medium": img.get("thumbnail", ""), "small": img.get("thumbnail", "")},
                            "download_url": image_url, "is_real": True,
                            "validation": validation, "validated": True,
                            "needs_style_transfer": False,
                        })
                    elif is_match and not style_ok:
                        style_mismatch_results.append({
                            "id": str(hash(image_url)), "source": "duckduckgo",
                            "source_type": "real", "url": img.get("url", ""),
                            "photographer": img.get("source", "Unknown"),
                            "width": 0, "height": 0, "alt": img.get("title", ""),
                            "src": {"original": image_url, "large": image_url,
                                    "medium": img.get("thumbnail", ""), "small": img.get("thumbnail", "")},
                            "download_url": image_url, "is_real": True,
                            "validation": validation, "validated": True,
                            "needs_style_transfer": True,
                        })
                    elif validation.get("confidence", 0) > 0 and len(fallback_results) < count:
                        fallback_results.append({
                            "id": str(hash(image_url)), "source": "duckduckgo",
                            "source_type": "real", "url": img.get("url", ""),
                            "photographer": img.get("source", "Unknown"),
                            "width": 0, "height": 0, "alt": img.get("title", ""),
                            "src": {"original": image_url, "large": image_url,
                                    "medium": img.get("thumbnail", ""), "small": img.get("thumbnail", "")},
                            "download_url": image_url, "is_real": True,
                            "validation": validation, "validated": True,
                            "needs_style_transfer": False,
                        })

            if len(validated_results) < count:
                time.sleep(2)

        if len(validated_results) < count:
            needed = count - len(validated_results)
            style_mismatch_fill = min(needed, len(style_mismatch_results))
            if style_mismatch_fill > 0:
                validated_results.extend(style_mismatch_results[:style_mismatch_fill])
                needed -= style_mismatch_fill
            if needed > 0:
                validated_results.extend(fallback_results[:needed])

        return validated_results

    def download(self, photo_url: str, save_path: str) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.google.com/"}
            response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            needs_convert = content_type and not content_type.startswith("image/jpeg")

            if not needs_convert:
                url_lower = photo_url.lower().split("?")[0]
                if any(url_lower.endswith(e) for e in [".png", ".webp", ".gif", ".avif", ".bmp", ".svg"]):
                    needs_convert = True

            if needs_convert:
                tmp_path = save_path + ".tmp"
                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                try:
                    from PIL import Image
                    img = Image.open(tmp_path)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        bg = Image.new('RGB', img.size, (0, 0, 0))
                        bg.paste(img, mask=img.convert('RGBA').split()[-1])
                        img = bg
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(save_path, 'JPEG', quality=95)
                except Exception:
                    import shutil
                    shutil.move(tmp_path, save_path)
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            else:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
            return save_path
        except Exception as e:
            raise


class ExaImageSearch:
    BASE_URL = "https://api.exa.ai/search"

    def __init__(self, api_key: str = None, validator=None):
        self.api_key = api_key or EXA_API_KEY
        if not self.api_key:
            raise ValueError("Exa API key not set")
        self.validator = validator

    def search(self, query: str, count: int = 5, orientation: str = "landscape",
               video_theme: str = "") -> List[Dict]:
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "query": f"{query} photo image",
            "numResults": count * 2,
            "type": "auto",
            "contents": {
                "extras": {"imageLinks": 3},
            },
        }
        try:
            response = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"  [exa] search error: {e}")
            return []

        raw_results = []
        for r in data.get("results", []):
            og_image = r.get("image", "")
            if og_image:
                raw_results.append({
                    "id": str(hash(og_image)), "source": "exa", "source_type": "real",
                    "url": r.get("url", ""), "photographer": "",
                    "width": 0, "height": 0, "alt": r.get("title", ""),
                    "src": {"original": og_image, "large": og_image,
                            "medium": og_image, "small": og_image},
                    "download_url": og_image, "is_real": True,
                })
            for img_url in (r.get("extras", {}).get("imageLinks") or []):
                if img_url and img_url not in {x["download_url"] for x in raw_results}:
                    raw_results.append({
                        "id": str(hash(img_url)), "source": "exa", "source_type": "real",
                        "url": r.get("url", ""), "photographer": "",
                        "width": 0, "height": 0, "alt": r.get("title", ""),
                        "src": {"original": img_url, "large": img_url,
                                "medium": img_url, "small": img_url},
                        "download_url": img_url, "is_real": True,
                    })
            if len(raw_results) >= count * 2:
                break

        if not self.validator or not video_theme:
            return raw_results[:count]

        return self._validate_results(raw_results, query, count, video_theme)

    def _validate_results(self, raw_results: list, query: str, count: int,
                          video_theme: str) -> List[Dict]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        validated = []
        style_mismatch = []
        fallback = []
        max_workers = 3

        def _validate_one(result):
            image_url = result.get("download_url", "")
            validation = self.validator.validate(
                image_url=image_url, query=query,
                video_theme=video_theme or None
            )
            is_match = validation["match"] and validation["confidence"] >= self.validator.confidence_threshold
            style_ok = validation.get("style_match", True) and validation.get("style_confidence", 0) >= self.validator.style_confidence_threshold
            return result, validation, is_match, style_ok

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_validate_one, r): r for r in raw_results}
            for future in as_completed(futures):
                if len(validated) >= count:
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    result, validation, is_match, style_ok = future.result()
                except Exception:
                    continue
                if is_match and style_ok:
                    result["validation"] = validation
                    result["validated"] = True
                    result["needs_style_transfer"] = False
                    validated.append(result)
                elif is_match and not style_ok:
                    result["validation"] = validation
                    result["validated"] = True
                    result["needs_style_transfer"] = True
                    style_mismatch.append(result)
                elif validation.get("confidence", 0) > 0 and len(fallback) < count:
                    result["validation"] = validation
                    result["validated"] = True
                    result["needs_style_transfer"] = False
                    fallback.append(result)

        if len(validated) < count:
            needed = count - len(validated)
            sm_fill = min(needed, len(style_mismatch))
            if sm_fill > 0:
                validated.extend(style_mismatch[:sm_fill])
                needed -= sm_fill
            if needed > 0:
                validated.extend(fallback[:needed])

        return validated[:count]

    def download(self, photo_url: str, save_path: str) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            needs_convert = content_type and not content_type.startswith("image/jpeg")

            if not needs_convert:
                url_lower = photo_url.lower().split("?")[0]
                if any(url_lower.endswith(e) for e in [".png", ".webp", ".gif", ".avif", ".bmp", ".svg"]):
                    needs_convert = True

            if needs_convert:
                tmp_path = save_path + ".tmp"
                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                try:
                    from PIL import Image
                    img = Image.open(tmp_path)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        bg = Image.new('RGB', img.size, (0, 0, 0))
                        bg.paste(img, mask=img.convert('RGBA').split()[-1])
                        img = bg
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(save_path, 'JPEG', quality=95)
                except Exception:
                    import shutil
                    shutil.move(tmp_path, save_path)
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            else:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
            return save_path
        except Exception as e:
            raise


class TavilyImageSearch:
    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str = None, validator=None):
        self.api_key = api_key or TAVILY_API_KEY
        if not self.api_key:
            raise ValueError("Tavily API key not set")
        self.validator = validator

    def search(self, query: str, count: int = 5, orientation: str = "landscape",
               video_theme: str = "") -> List[Dict]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": count,
            "topic": "general",
            "include_images": True,
        }
        try:
            response = requests.post(self.BASE_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"  [tavily] search error: {e}")
            return []

        raw_results = []
        for img in data.get("images", []):
            if isinstance(img, dict):
                image_url = img.get("url", "")
                alt = img.get("title", "") or img.get("description", "")
            else:
                image_url = str(img)
                alt = ""
            if not image_url:
                continue
            raw_results.append({
                "id": str(hash(image_url)), "source": "tavily", "source_type": "real",
                "url": "", "photographer": "",
                "width": 0, "height": 0, "alt": alt,
                "src": {"original": image_url, "large": image_url,
                        "medium": image_url, "small": image_url},
                "download_url": image_url, "is_real": True,
            })
            if len(raw_results) >= count:
                break

        if not self.validator or not video_theme:
            return raw_results[:count]

        return self._validate_results(raw_results, query, count, video_theme)

    def _validate_results(self, raw_results: list, query: str, count: int,
                          video_theme: str) -> List[Dict]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        validated = []
        style_mismatch = []
        fallback = []
        max_workers = 3

        def _validate_one(result):
            image_url = result.get("download_url", "")
            validation = self.validator.validate(
                image_url=image_url, query=query,
                video_theme=video_theme or None
            )
            is_match = validation["match"] and validation["confidence"] >= self.validator.confidence_threshold
            style_ok = validation.get("style_match", True) and validation.get("style_confidence", 0) >= self.validator.style_confidence_threshold
            return result, validation, is_match, style_ok

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_validate_one, r): r for r in raw_results}
            for future in as_completed(futures):
                if len(validated) >= count:
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    result, validation, is_match, style_ok = future.result()
                except Exception:
                    continue
                if is_match and style_ok:
                    result["validation"] = validation
                    result["validated"] = True
                    result["needs_style_transfer"] = False
                    validated.append(result)
                elif is_match and not style_ok:
                    result["validation"] = validation
                    result["validated"] = True
                    result["needs_style_transfer"] = True
                    style_mismatch.append(result)
                elif validation.get("confidence", 0) > 0 and len(fallback) < count:
                    result["validation"] = validation
                    result["validated"] = True
                    result["needs_style_transfer"] = False
                    fallback.append(result)

        if len(validated) < count:
            needed = count - len(validated)
            sm_fill = min(needed, len(style_mismatch))
            if sm_fill > 0:
                validated.extend(style_mismatch[:sm_fill])
                needed -= sm_fill
            if needed > 0:
                validated.extend(fallback[:needed])

        return validated[:count]

    def download(self, photo_url: str, save_path: str) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(photo_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            needs_convert = content_type and not content_type.startswith("image/jpeg")

            if not needs_convert:
                url_lower = photo_url.lower().split("?")[0]
                if any(url_lower.endswith(e) for e in [".png", ".webp", ".gif", ".avif", ".bmp", ".svg"]):
                    needs_convert = True

            if needs_convert:
                tmp_path = save_path + ".tmp"
                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                try:
                    from PIL import Image
                    img = Image.open(tmp_path)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        bg = Image.new('RGB', img.size, (0, 0, 0))
                        bg.paste(img, mask=img.convert('RGBA').split()[-1])
                        img = bg
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(save_path, 'JPEG', quality=95)
                except Exception:
                    import shutil
                    shutil.move(tmp_path, save_path)
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            else:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
            return save_path
        except Exception as e:
            raise


class ImageSearch:
    def __init__(self, pexels_key: str = None, use_duckduckgo: bool = True,
                 validator=None, output_dir: str = None,
                 exa_key: str = None, tavily_key: str = None):
        self.output_dir = Path(output_dir or str(SEARCH_RESULTS_DIR))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.services = {}

        if pexels_key or PEXELS_API_KEY:
            self.services["pexels"] = PexelsAPI(pexels_key or PEXELS_API_KEY)

        if use_duckduckgo:
            self.services["real"] = DuckDuckGoImageSearch(validator=validator)

        if exa_key or EXA_API_KEY:
            try:
                self.services["exa"] = ExaImageSearch(exa_key or EXA_API_KEY, validator=validator)
            except ValueError:
                pass

        if tavily_key or TAVILY_API_KEY:
            try:
                self.services["tavily"] = TavilyImageSearch(tavily_key or TAVILY_API_KEY, validator=validator)
            except ValueError:
                pass

        self.validator = validator

    def search(self, query: str, source: str = "stock", stock_service: str = "pexels",
               count: int = 5, orientation: str = "landscape", save: bool = False,
               validate: bool = None, video_theme: str = "") -> List[Dict]:
        all_results = []
        if source in ["stock", "both"]:
            if stock_service in self.services:
                api = self.services[stock_service]
                stock_results = api.search(query, count, orientation)
                all_results.extend(stock_results)

        if source in ["real", "both"]:
            if "real" not in self.services:
                pass
            else:
                api = self.services["real"]
                real_results = api.search(query, count, orientation, validate=validate, video_theme=video_theme)
                all_results.extend(real_results)

        if source in ["exa", "both"] and "exa" in self.services:
            api = self.services["exa"]
            exa_results = api.search(query, count, orientation, video_theme=video_theme)
            all_results.extend(exa_results)

        if source in ["tavily", "both"] and "tavily" in self.services:
            api = self.services["tavily"]
            tavily_results = api.search(query, count, orientation, video_theme=video_theme)
            all_results.extend(tavily_results)

        if save:
            for i, result in enumerate(all_results, 1):
                source_type = result.get("source_type", "unknown")
                filename = f"{result['source']}_{result['id']}_{i}.jpg"
                save_path = self.output_dir / filename
                try:
                    if source_type == "stock":
                        api = self.services.get(stock_service)
                    elif result["source"] in ("exa", "tavily"):
                        api = self.services.get(result["source"])
                    else:
                        api = self.services.get("real")
                    if api:
                        api.download(result["download_url"], str(save_path))
                        result["local_path"] = str(save_path)
                        time.sleep(0.5)
                except Exception as e:
                    print(f"     Download error: {e}")

        return all_results

    def search_person(self, name: str, source: str = "real", count: int = 3,
                      validate: bool = None, video_theme: str = "") -> List[Dict]:
        return self.search(name, source=source, count=count, orientation="portrait",
                           validate=validate, video_theme=video_theme)

    def search_location(self, name: str, source: str = "stock", count: int = 3,
                        validate: bool = None, video_theme: str = "") -> List[Dict]:
        return self.search(name, source=source, count=count, orientation="landscape",
                           validate=validate, video_theme=video_theme)

    def search_object(self, name: str, source: str = "both", count: int = 3,
                      validate: bool = None, video_theme: str = "") -> List[Dict]:
        return self.search(name, source=source, count=count, orientation="landscape",
                           validate=validate, video_theme=video_theme)

# 🔍 Поиск стоковых изображений

Модуль для поиска бесплатных стоковых изображений из Pexels, Unsplash и Pixabay.

## 📋 Требования

- Python 3.8+
- API ключи (бесплатные):
  - Pexels: https://www.pexels.com/api/
  - Unsplash: https://unsplash.com/developers
  - Pixabay: https://pixabay.com/api/docs/

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install requests
```

### 2. Получение API ключей

Pexels (рекомендуется, 200 запросов/час бесплатно):
1. Зарегистрируйтесь на https://www.pexels.com
2. Перейдите в https://www.pexels.com/api/
3. Нажмите "Get Started" и получите ключ

Unsplash (50 запросов/час бесплатно):
1. Зарегистрируйтесь на https://unsplash.com
2. Создайте приложение на https://unsplash.com/developers
3. Получите Access Key

Pixabay (5000 запросов/час бесплатно):
1. Зарегистрируйтесь на https://pixabay.com
2. Получите ключ на https://pixabay.com/api/docs/

### 3. Использование

#### Через командную строку

```bash
# Базовый поиск
python stock_image_search.py "космос" --service pexels --count 5

# С API ключом
python stock_image_search.py "Илон Маск" --api-key YOUR_KEY --service pexels

# С сохранением изображений
python stock_image_search.py "природа" --api-key YOUR_KEY --save --output ./images

# Поиск портретов
python stock_image_search.py "бизнесмен" --orientation portrait --count 3

# Сохранение результатов в JSON
python stock_image_search.py "город" --json
```

#### Программно

```python
from stock_image_search import StockImageSearch

# Инициализация
searcher = StockImageSearch(pexels_key="your_key")

# Поиск
results = searcher.search(
    query="космос",
    service="pexels",
    count=5,
    orientation="landscape",
    save=True
)

# Поиск персоны
person_results = searcher.search_person("Илон Маск", count=3)

# Поиск локации
location_results = searcher.search_location("Париж", count=5)
```

## 🎯 Параметры CLI

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `query` | Поисковый запрос | (обязательно) |
| `--service` | Сервис: pexels, unsplash, pixabay | pexels |
| `--api-key` | API ключ | env переменная |
| `--count` | Количество изображений | 5 |
| `--orientation` | Ориентация: landscape, portrait, square | landscape |
| `--output` | Папка для сохранения | ./stock_images |
| `--save` | Скачать изображения | False |
| `--json` | Сохранить JSON | False |

## 📄 Структура результата (JSON)

```json
[
  {
    "id": "12345",
    "source": "pexels",
    "url": "https://www.pexels.com/photo/...",
    "photographer": "John Doe",
    "photographer_url": "https://www.pexels.com/@johndoe",
    "width": 1920,
    "height": 1080,
    "alt": "Описание изображения",
    "src": {
      "original": "...",
      "large": "...",
      "medium": "...",
      "small": "..."
    },
    "download_url": "...",
    "local_path": "./stock_images/pexels_12345_1.jpg"
  }
]
```

## 🔗 Интеграция с Video Generator V2

Модуль автоматически используется в `video_generator_v2.py` для:
1. Поиска реальных фото персон из assets_manifest
2. Поиска стоковых фото для фонов
3. Fallback перед генерацией через Whisk

```python
from video_generator_v2 import VideoGeneratorV2

generator = VideoGeneratorV2(
    fireworks_api_key="fw_key",
    whisk_cookie="whisk_cookie",
    pexels_api_key="pexels_key",
    use_stock_first=True  # Сначала искать стоки, потом генерировать
)
```

## 💡 Примеры

### Поиск фото для персоны

```bash
python stock_image_search.py "Илон Маск" --service pexels --orientation portrait --count 3 --save
```

### Поиск фото для локации

```bash
python stock_image_search.py "Нью-Йорк таймс сквер" --service pexels --orientation landscape --count 5 --save
```

### Поиск объектов

```bash
python stock_image_search.py "красный спорткар" --service pixabay --count 10 --save
```

## 🆚 Сравнение сервисов

| Сервис | Бесплатно | Качество | Скорость |
|--------|-----------|----------|----------|
| Pexels | 200/час | ⭐⭐⭐⭐⭐ | Быстро |
| Unsplash | 50/час | ⭐⭐⭐⭐⭐ | Средне |
| Pixabay | 5000/час | ⭐⭐⭐⭐ | Быстро |

## ⚠️ Лицензирование

Все изображения с Pexels, Unsplash и Pixabay бесплатны для коммерческого использования.
Но всегда проверяйте лицензию конкретного изображения.

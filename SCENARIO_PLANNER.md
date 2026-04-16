# 🎬 Планировщик видео-сценариев

Генератор детальных сценариев для видео с использованием Fireworks AI (Gemma 4). Создает сценарий с промптами для каждой сцены, таймингами, текстом озвучки и параметрами для генерации изображений.

## 📋 Требования

- Python 3.8+
- API ключ Fireworks AI

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements_scenario.txt
```

### 2. Получение API ключа

1. Зарегистрируйтесь на [fireworks.ai](https://app.fireworks.ai)
2. Перейдите в Dashboard → API Keys
3. Создайте новый ключ

### 3. Использование

#### Базовая генерация

```bash
python video_scenario_planner.py "Космическое путешествие" --api-key YOUR_KEY
```

#### С указанием параметров

```bash
python video_scenario_planner.py "Романтическое свидание в Париже" --api-key YOUR_KEY --duration 45 --style cinematic --language ru
```

#### Сохранение в файл

```bash
python video_scenario_planner.py "Приключение в лесу" --api-key YOUR_KEY --output my_scenario.json
```

#### Доработка существующего сценария

```bash
python video_scenario_planner.py --api-key YOUR_KEY --refine my_scenario.json --feedback "Сделай сцены длиннее и добавь больше экшена"
```

## ⚙️ Конфигурация

В начале файла `video_scenario_planner.py`:

```python
CONFIG = {
    "api_key": "",        # Fireworks API key
    "model": "accounts/fireworks/models/gemma-4-31b-it-nvfp4",
    "temperature": 0.8,
    "max_tokens": 4096,
    "default_language": "ru",
}
```

Или через переменную окружения:

```powershell
$env:FIREWORKS_API_KEY = "your_key_here"
```

## 📄 Структура сценария (JSON)

```json
{
  "title": "Название видео",
  "description": "Описание",
  "total_duration_sec": 30,
  "scenes": [
    {
      "scene_number": 1,
      "start_time_sec": 0,
      "duration_sec": 5,
      "voiceover_text": "Текст для озвучки",
      "image_prompt": "Промпт для Whisk API",
      "image_aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
      "image_model": "IMAGEN_3_5",
      "image_seed": 0,
      "mood": "Настроение",
      "transition": "Тип перехода"
    }
  ],
  "notes": "Заметки"
}
```

## 🎯 Параметры

| Параметр | Краткий | Описание | По умолчанию |
|----------|---------|----------|--------------|
| `topic` | - | Тема видео | (интерактивно) |
| `--api-key` | - | Fireworks API key | `FIREWORKS_API_KEY` |
| `--language` | `-l` | Язык озвучки: ru, en | `ru` |
| `--duration` | `-d` | Целевая длительность (сек) | `30` |
| `--style` | `-s` | Стиль видео | - |
| `--scenes` | `-n` | Количество сцен | - |
| `--output` | `-o` | Файл сохранения | `scenario_*.json` |
| `--refine` | `-r` | Файл для доработки | - |
| `--feedback` | `-f` | Фидбек для доработки | - |

## 🔗 Интеграция с генератором изображений

Сценарий содержит готовые промпты и параметры для `image_generator.py`:

```python
import json
from video_scenario_planner import VideoScenarioPlanner
from image_generator import ImageGenerator

# Загрузка сценария
planner = VideoScenarioPlanner()
scenario = planner.load_scenario("scenario.json")

# Генерация изображений для каждой сцены
generator = ImageGenerator(cookie="your_cookie")

for scene in scenario["scenes"]:
    generator.generate(
        prompt=scene["image_prompt"],
        model=scene["image_model"],
        aspect_ratio=scene["image_aspect_ratio"],
        seed=scene["image_seed"],
    )
```

## 💡 Примеры

### Короткое промо (15 сек)

```bash
python video_scenario_planner.py "Промо нового смартфона" --duration 15 --scenes 3 --style minimal
```

### История (45 сек)

```bash
python video_scenario_planner.py "Путешествие на Марс" --duration 45 --style cinematic --output mars.json
```

### Доработка

```bash
python video_scenario_planner.py --refine mars.json --feedback "Добавь больше юмора и сделай концовку драматичнее"
```

# 🎬 Планировщик видео-сценариев V2

Генератор детальных JSON-планов для видео V2 с использованием Fireworks AI. Создает сценарий с разделением на фоновые слои и оверлеи, манифестом ассетов и поддержкой реальных персон.

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
python video_scenario_planner_v2.py "Космическое путешествие" --api-key YOUR_KEY
```

#### С указанием параметров

```bash
python video_scenario_planner_v2.py "Романтическое свидание в Париже" --api-key YOUR_KEY --duration 45 --style cinematic --language ru
```

#### Сохранение в файл

```bash
python video_scenario_planner_v2.py "Приключение в лесу" --api-key YOUR_KEY --output my_scenario.json
```

#### Доработка существующего сценария

```bash
python video_scenario_planner_v2.py --api-key YOUR_KEY --refine my_scenario.json --feedback "Сделай сцены длиннее и добавь больше экшена"
```

## ⚙️ Конфигурация

В начале файла `video_scenario_planner_v2.py`:

```python
CONFIG = {
    "api_key": "",        # Fireworks API key
    "model": "accounts/fireworks/models/qwen3p6-plus",
    "temperature": 0.7,
    "max_tokens": 4096,
    "default_language": "ru",
}
```

Или через переменную окружения:

```powershell
$env:FIREWORKS_API_KEY = "your_key_here"
```

## 📄 Структура сценария V2 (JSON)

```json
{
  "metadata": {
    "vibe": "Стиль видео",
    "tempo": "Темп",
    "assets": ["список ассетов"]
  },
  "timeline": [
    {
      "voiceover": "Текст для озвучки",
      "background": {
        "type": "stock_video | generated_image | person_photo",
        "prompt": "Промпт для фона"
      },
      "overlays": [
        {
          "type": "thesis | quote | nameplate",
          "text": "Текст оверлея"
        }
      ]
    }
  ],
  "assets_manifest": [
    {
      "type": "person | location | object",
      "name": "Имя сущности",
      "description": "Описание для поиска/генерации"
    }
  ]
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
| `--output` | `-o` | Файл сохранения | `scenario_v2_*.json` |
| `--refine` | `-r` | Файл для доработки | - |
| `--feedback` | `-f` | Фидбек для доработки | - |

## 🔗 Интеграция с генератором видео V2

Сценарий V2 содержит готовые промпты и параметры для `video_generator_v2.py`:

```python
from video_scenario_planner_v2 import VideoScenarioPlannerV2
from video_generator_v2 import VideoGeneratorV2

# Загрузка сценария
planner = VideoScenarioPlannerV2()
scenario = planner.load_scenario("scenario.json")

# Генерация видео
generator = VideoGeneratorV2(whisk_cookie="your_cookie")
video_path = generator.generate_video_from_scenario(scenario)
```

## 💡 Примеры

### Короткое промо (15 сек)

```bash
python video_scenario_planner_v2.py "Промо нового смартфона" --duration 15 --scenes 3 --style minimal
```

### История (45 сек)

```bash
python video_scenario_planner_v2.py "Путешествие на Марс" --duration 45 --style cinematic --output mars.json
```

### Доработка

```bash
python video_scenario_planner_v2.py --refine mars.json --feedback "Добавь больше юмора и сделай концовку драматичнее"
```

## 🆚 Отличия от V1

| Функция | V1 | V2 |
|---------|----|----|
| Структура | Плоский список сцен | Timeline с фонами и оверлеями |
| Ассеты | Только промпты | Assets manifest с типами |
| Персоны | Нет поддержки | Автоматическое создание person объектов |
| Оверлеи | Текст озвучки на экран | Умные тезисы (2-4 слова) |
| Фоны | Одно изображение | Разделение на stock/generated/person |

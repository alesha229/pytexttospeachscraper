# TTS Engine Documentation

Консольный модуль для преобразования текста в речь через InWorld API.

## Быстрый старт

### Установка

```bash
pip install requests
```

### Базовое использование

```bash
# Озвучить текст
python tts_engine.py --text "Привет мир!" --voice Svetlana

# Озвучить файл
python tts_engine.py --file book.txt --voice Dmitry --output book.wav

# Список голосов
python tts_engine.py --list-voices
```

---

## CLI команды

### Озвучка текста

```bash
python tts_engine.py --text "Ваш текст" --voice <голос> [опции]
```

### Озвучка файла

```bash
python tts_engine.py --file input.txt --voice <голос> [опции]
```

### Список доступных голосов

```bash
# Все голоса
python tts_engine.py --list-voices

# Фильтр по языку
python tts_engine.py --list-voices --lang-filter ru
python tts_engine.py --list-voices --lang-filter en
```

---

## Опции CLI

| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--text` | `-t` | Текст для озвучки | — |
| `--file` | `-f` | Путь к текстовому файлу | — |
| `--list-voices` | `-l` | Показать список голосов | — |
| `--voice` | `-v` | ID или имя голоса | — |
| `--output` | `-o` | Путь к выходному WAV | auto |
| `--max-chars` | `-m` | Макс. символов на фрагмент | `1000` |
| `--output-dir` | `-d` | Папка для обычных файлов | `output/` |
| `--batch-dir` | — | Папка для batch файлов | `output_batch/` |
| `--lang-filter` | — | Фильтр языков для `--list-voices` | — |

---

## Примеры CLI

### Простая генерация

```bash
python tts_engine.py -t "Привет! Как дела?" -v Svetlana
# → output/Привет_Как_дел.wav
```

### Batch-генерация большого файла

```bash
python tts_engine.py -f novel_chapter1.txt -v Nikolai -o novel.wav
# 📝 5230 символов → 6 фрагментов
# → output_batch/novel.wav
# → output_batch/novel_parts/part001.wav ... part006.wav
```

### Кастомный размер фрагмента

```bash
python tts_engine.py -f long.txt -v Elena -m 500 -o short_chunks.wav
# Разбиение по 500 символов вместо 1000
```

### Фильтрация голосов

```bash
python tts_engine.py -l --lang-filter ru
# Покажет только русские голоса: Svetlana, Elena, Dmitry, Nikolai
```

---

## Программное использование (импорт модуля)

### Базовый пример

```python
from tts_engine import tts

# Автоматический выбор single/batch режима
success = tts(
    text="Привет мир!",
    voice_id="Svetlana",
    output_path="output/hello.wav"
)

if success:
    print("Готово!")
```

### Single-режим (короткий текст)

```python
from tts_engine import tts_single

success = tts_single(
    text="Короткая фраза",
    voice_id="Dmitry",
    output_path="output/phrase.wav"
)
```

### Batch-режим (длинный текст)

```python
from tts_engine import tts_batch

with open("book.txt", "r", encoding="utf-8") as f:
    text = f.read()

success = tts_batch(
    text=text,
    voice_id="Elena",
    output_path="output_batch/book.wav",
    max_chunk=1000,  # размер одного части
    on_progress=lambda msg: print(f"  → {msg}")
)
```

### С callback прогресса

```python
from tts_engine import tts

def on_progress(message: str):
    """Callback для отслеживания прогресса"""
    print(f"[TTS] {message}")
    
    # Можно интегрировать с GUI:
    # progress_bar.set(message)
    # status_label.config(text=message)

tts(
    text="Очень длинный текст для генерации...",
    voice_id="Nikolai",
    output_path="output/long.wav",
    on_progress=on_progress
)
```

### Получение списка голосов

```python
from tts_engine import load_voices, get_voice_map

# Загрузить список голосов
voices = load_voices()
for v in voices:
    print(f"{v.display_name}: {v.languages}")

# Получить маппинг {имя: voice_id}
voice_map = get_voice_map()
print(voice_map["Svetlana"])  # → "voice_id_..."
```

### Умное разбиение текста

```python
from tts_engine import split_text_smart

text = "Длинный текст..."  # 5000 символов

chunks = split_text_smart(text, max_length=1000)
print(f"Разбито на {len(chunks)} частей")

for i, chunk in enumerate(chunks):
    print(f"Часть {i+1}: {len(chunk)} символов")
```

---

## Структура файлов

```
tts_engine.py          # Основной модуль
example_usage.py       # Примеры использования
voices.json            # Список голосов
output/                # Обычные аудио
output_batch/          # Batch аудио
  └── {name}_parts/    # Куски batch файла
      ├── part001.wav
      ├── part002.wav
      └── ...
```

---

## Batch-режим: как работает

1. **Разбиение** — текст делится на части по `max_chunk` символов
2. **Умный сплит** — не обрывает слова/предложения (приоритет: абзацы → предложения → запятые → пробелы)
3. **Генерация** — каждый фрагмент отправляется на сервер отдельно
4. **Сохранение** — куски сохраняются в подпапку `{имя}_parts/`
5. **Объединение** — все части сливаются в один WAV файл
6. **Куски сохраняются** — не удаляются для возможного переиспользования

### Пример batch-генерации

```
Вход: 5000 символов
Разбиение: 5 частей по ~1000 символов

output_batch/
├── book.wav              # Объединённый файл
└── book_parts/
    ├── part001.wav       # 0-1000 символов
    ├── part002.wav       # 1000-2000 символов
    ├── part003.wav       # 2000-3000 символов
    ├── part004.wav       # 3000-4000 символов
    └── part005.wav       # 4000-5000 символов
```

---

## API Reference

### `tts(text, voice_id, output_path, max_chunk=1000, on_progress=None)`
Универсальная функция. Авто-выбор single/batch режима.

**Args:**
- `text` (str): Текст для озвучки
- `voice_id` (str): ID голоса
- `output_path` (str): Путь к выходному файлу
- `max_chunk` (int): Максимальный размер фрагмента
- `on_progress` (Callable[[str], None]): Callback прогресса

**Returns:** `bool` — `True` если успешно

---

### `tts_single(text, voice_id, output_path, on_progress=None)`
Генерация одного фрагмента (текст ≤ `max_chunk`).

---

### `tts_batch(text, voice_id, output_path, max_chunk=1000, on_progress=None)`
Batch-генерация с разбиением (текст > `max_chunk`).

---

### `split_text_smart(text, max_length=1000) → List[str]`
Умное разбиение текста без обрыва слов/предложений.

---

### `merge_wav_files(file_paths, output_path) → bool`
Объединение нескольких WAV файлов в один.

---

### `load_voices(voices_file=None) → List[VoiceInfo]`
Загрузка списка голосов из `voices.json`.

---

### `get_voice_map(voices_file=None) → dict`
Возвращает словарь `{display_name: voice_id}`.

---

### `list_voices(voices_file=None, lang_filter=None)`
Вывод списка голосов в консоль.

---

## Доступные голоса

| Голос | Язык | Описание |
|-------|------|----------|
| Svetlana | ru | Мягкий высокий женский голос |
| Elena | ru | Чистый средний женский голос |
| Dmitry | ru | Глубокий хриплый мужской голос |
| Nikolai | ru | Глубокий resonant мужской голос |
| *130+ других* | en, de, fr... | См. `--list-voices` |

---

## Конфигурация

Глобальные настройки в `tts_engine.py`:

```python
URL = "https://inworld.ai/api/create-speech"
MAX_CHARS = 1000           # Размер фрагмента по умолчанию
SAMPLE_RATE = 48000        # Частота дискретизации

COOKIES = {
    "inworld_uid": "YOUR_UID_HERE"
}
```

---

## Troubleshooting

### Ошибка "Голоса не найдены"
Проверьте наличие `voices.json` в той же папке что и `tts_engine.py`.

### Ошибка сервера 401/403
Обновите `inworld_uid` в `COOKIES`.

### Текст обрезывается
Увеличьте `--max-chars` или проверьте что текст корректно кодируется в UTF-8.

### Нет звука при воспроизведении
Проверьте что WAV файл создан и не пустой (размер > 44 байт).

---

## Лицензия

MIT

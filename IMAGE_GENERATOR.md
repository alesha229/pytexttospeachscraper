# 🎨 Консольный генератор изображений

Генератор изображений на основе Whisk API (Google Labs) с использованием моделей IMAGEN.

## 📋 Требования

- Python 3.8+
- Cookie сессии Google аккаунта

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements_images.txt
```

### 2. Получение cookie

Для работы API требуется cookie сессии Google аккаунта:

1. Войдите в [Google Whisk Labs](https://labs.google/whisk)
2. Откройте DevTools (F12) → Application → Cookies
3. Скопируйте значение `__Secure-1PSID`

### 3. Использование

#### Базовая генерация

```bash
python image_generator.py "Красивый закат на море" --cookie YOUR_COOKIE
```

#### С указанием параметров

```bash
python image_generator.py "Cyberpunk city at night" --model imagen4 --aspect portrait --cookie YOUR_COOKIE
```

#### С seed для воспроизводимости

```bash
python image_generator.py "Cat astronaut" --seed 42 --cookie YOUR_COOKIE
```

## ⚙️ Параметры

| Параметр | Краткий | Описание | По умолчанию |
|----------|---------|----------|--------------|
| `prompt` | - | Текстовое описание изображения | (обязательно) |
| `--cookie` | `-c` | Cookie сессии Google | `WHISK_COOKIE` из окружения |
| `--model` | `-m` | Модель: `imagen3`, `imagen3.5`, `imagen4` | `imagen3.5` |
| `--aspect` | `-a` | Соотношение: `square`, `portrait`, `landscape` | `landscape` |
| `--seed` | `-s` | Seed для воспроизводимости (0 = случайный) | `0` |
| `--dir` | `-d` | Папка для сохранения | `./output` |

## 🔧 Переменные окружения

Можно установить cookie через переменную окружения:

**PowerShell:**
```powershell
$env:WHISK_COOKIE = "your_cookie_here"
python image_generator.py "prompt"
```

**CMD:**
```cmd
set WHISK_COOKIE=your_cookie_here
python image_generator.py "prompt"
```

## 📸 Примеры

### Квадратное изображение

```bash
python image_generator.py "Cute cat portrait" --aspect square --model imagen4
```

### Вертикальный постер

```bash
python image_generator.py "Fantasy castle in clouds" --aspect portrait
```

### Воспроизводимый результат

```bash
python image_generator.py "Space station" --seed 123 --aspect landscape
python image_generator.py "Space station" --seed 123 --aspect landscape
# Оба вызова создадут одинаковые изображения
```

## 📁 Структура выходных файлов

Изображения сохраняются в папку `./output` (или указанную через `--dir`) с именем:
```
generated_{timestamp}_{seed}.png
```

## ⚠️ Важно

- Cookie имеет срок действия - при ошибках аутентификации получите новый
- Генерация может занять 10-30 секунд
- API может иметь лимиты на количество запросов

## 🐛 Решение проблем

**Ошибка аутентификации:** Проверьте правильность cookie

**Ошибка соединения:** Проверьте интернет-соединение

**Пустой ответ:** Возможно, API временно недоступен - повторите запрос

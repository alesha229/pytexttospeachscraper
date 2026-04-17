"""
Модуль генерации сценария видео с использованием Fireworks AI
Создает детальный сценарий с промптами для изображений, таймингами и текстом озвучки

Использование:
    python video_scenario_planner.py "Тема видео"
    python video_scenario_planner.py "Тема" --language en --duration 60
    python video_scenario_planner.py --topic "Тема" --style cinematic --scenes 5

Вход:
    - topic (str): Тема видео (обязательно)
    - api-key (str): Fireworks API key (или через FIREWORKS_API_KEY)
    - language (str): Язык озвучки (по умолчанию "ru")
    - duration (int): Целевая длительность в секундах (по умолчанию 30)
    - style (str): Стиль видео (опционально)
    - scenes (int): Количество сцен (опционально)

Выход:
    - JSON файл сценария (по умолчанию scenario_{topic}.json)
    - Структура JSON:
        {
            "title": "Название",
            "description": "Описание",
            "total_duration_sec": 30,
            "scenes": [
                {
                    "scene_number": 1,
                    "start_time_sec": 0,
                    "duration_sec": 5,
                    "voiceover_text": "Текст озвучки",
                    "image_prompt": "Промпт для изображения",
                    "image_aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
                    "image_model": "IMAGEN_3_5",
                    "image_seed": 0,
                    "mood": "Настроение",
                    "transition": "fade"
                }
            ],
            "notes": "Заметки"
        }
"""

import json
import os
from typing import Optional
from openai import OpenAI

# ============================================================
# ⚙️ КОНФИГУРАЦИЯ
# ============================================================
CONFIG = {
    "api_key": os.environ.get("FIREWORKS_API_KEY", ""),
    "model": "accounts/fireworks/models/qwen3p6-plus",
    "temperature": 0.7,
    "max_tokens": 4096,
    "default_language": "ru",
}
# ============================================================


class FireworksClient:
    """Клиент для Fireworks AI API через OpenAI-совместимый интерфейс"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["api_key"] or os.environ.get("FIREWORKS_API_KEY")
        if not self.api_key:
            raise ValueError("API ключ не указан. Установите FIREWORKS_API_KEY или укажите в CONFIG")
        
        self.client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self.api_key,
        )
    
    def generate(self, messages: list, model: str = None, temperature: float = None, max_tokens: int = None) -> str:
        """
        Генерация ответа от LLM
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            model: Модель (если None, используется CONFIG)
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Текст ответа
        """
        # Fireworks AI требует stream=true для max_tokens > 4096
        use_stream = max_tokens is not None and max_tokens > 4000
        
        print(f"  🔌 Запрос к LLM: model={model or CONFIG['model']}, max_tokens={max_tokens or CONFIG['max_tokens']}, stream={use_stream}")
        
        try:
            response = self.client.chat.completions.create(
                model=model or CONFIG["model"],
                messages=messages,
                temperature=temperature if temperature is not None else CONFIG["temperature"],
                max_tokens=max_tokens or CONFIG["max_tokens"],
                stream=use_stream,
            )
            
            if use_stream:
                print("  📡 Получаем ответ через стриминг...")
                full_response = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                if not full_response:
                    raise ValueError("API вернул пустой стрим. Проверьте API ключ и модель.")
                print(f"  ✅ Получено {len(full_response)} символов")
                return full_response
            else:
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("API вернул пустое содержание. Проверьте API ключ.")
                print(f"  ✅ Получено {len(content)} символов")
                return content
        except Exception as e:
            print(f"❌ Ошибка запроса к LLM: {e}")
            raise


class VideoScenarioPlanner:
    """
    Планировщик видео-сценария
    Создет детальный сценарий с промптами для каждой сцены, таймингами и текстом озвучки
    """
    
    SYSTEM_PROMPT = """Ты - профессиональный сценарист и режиссер видеоконтента.
Твоя задача - создавать детальные сценарии для коротких видео.

Ты должен вернуть JSON в следующем формате:
{
  "title": "Название видео",
  "description": "Краткое описание",
  "total_duration_sec": 30,
  "scenes": [
    {
      "scene_number": 1,
      "start_time_sec": 0,
      "duration_sec": 35,
      "voiceover_text": "Длинный осмысленный текст для озвучки. Здесь должно быть много текста, чтобы озвучка заняла 30-40 секунд. Текст должен быть информативным, связным и интересным для слушателя. Каждая сцена должна содержать подробное объяснение темы.",
      "image_prompt": "Детальный промпт для генерации изображения через Whisk API (IMAGEN). Изображение должно быть качественным и информативным, так как оно будет на экране 30-40 секунд.",
      "image_aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
      "image_model": "IMAGEN_3_5",
      "image_seed": 0,
      "mood": "Настроение сцены: информативное, вдохновляющее, серьезное",
      "transition": "Тип перехода к следующей сцене: fade, cut, dissolve"
    }
  ],
  "notes": "Дополнительные заметки для создателя видео"
}

ПРАВИЛА:
- КАЖДАЯ СЦЕНА ДОЛЖНА БЫТЬ ДЛИТЕЛЬНОСТЬЮ 30-40 СЕКУНД
- voiceover_text ДОЛЖЕН БЫТЬ ДЛИННЫМ (минимум 60-80 слов на сцену)
- image_prompt должен быть на английском для лучшего качества генерации
- voiceover_text должен быть на языке, указанном пользователем
- Количество сцен: 2-4 (не больше)
- Общая длительность: 60-120 секунд
- Изображения должны быть качественными и детальными, так как они будут на экране долго"""
    
    def __init__(self, api_key: str = None):
        self.client = FireworksClient(api_key)
    
    def create_scenario(
        self,
        topic: str,
        language: str = None,
        target_duration: int = 30,
        style: str = None,
        num_scenes: int = None,
    ) -> dict:
        """
        Создание сценария видео
        
        Args:
            topic: Тема/идея видео
            language: Язык озвучки (ru, en)
            target_duration: Целевая длительность в секундах
            style: Стиль видео (cinematic, cartoon, realistic, minimal и т.д.)
            num_scenes: Желаемое количество сцен
            
        Returns:
            JSON сценария
        """
        lang = language or CONFIG["default_language"]
        
        user_prompt = f"""Создай сценарий для видео.

ТЕМА: {topic}
ЯЗЫК озвучки: {lang}
ЦЕЛЕВАЯ длительность: {target_duration} секунд"""
        
        if style:
            user_prompt += f"\nСТИЛЬ: {style}"
        
        if num_scenes:
            user_prompt += f"\nКОЛИЧЕСТВО сцен: {num_scenes}"
        
        user_prompt += """

Верни ТОЛЬКО JSON без markdown, без пояснений, только валидный JSON."""
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        # Используем стриминг для длинных ответов
        response = self.client.generate(messages, max_tokens=8192)
        
        if response is None:
            raise ValueError("LLM вернула пустой ответ. Проверьте API ключ и подключение.")
        
        # Извлечение JSON из ответа (убираем markdown code blocks если есть)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
        if response.endswith("```"):
            response = response.rsplit("\n", 1)[0]
        response = response.strip()
        
        # Убираем ```json если есть
        if response.startswith("```json"):
            response = response[7:].strip()
        
        try:
            scenario = json.loads(response)
            return scenario
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ модели (первые 500 символов):\n{response[:500]}...")
            
            # Пытаемся найти JSON в ответе
            json_start = response.find("{")
            json_end = response.rfind("}")
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                try:
                    extracted_json = response[json_start:json_end+1]
                    # Пытаемся исправить обрезанные строки
                    if extracted_json.count('"') % 2 != 0:
                        # Нечетное количество кавычек - обрезанная строка
                        last_quote = extracted_json.rfind('"')
                        if last_quote > 0:
                            extracted_json = extracted_json[:last_quote] + '"}'
                    
                    scenario = json.loads(extracted_json)
                    print("✅ JSON успешно извлечен из ответа (с исправлениями)")
                    return scenario
                except json.JSONDecodeError as e2:
                    print(f"⚠ Не удалось исправить JSON: {e2}")
            
            raise ValueError("Не удалось извлечь валидный JSON из ответа модели. Попробуйте уменьшить количество сцен или длительность.")
    
    def refine_scenario(
        self,
        scenario: dict,
        feedback: str,
    ) -> dict:
        """
        Доработка существующего сценария по фидбеку
        
        Args:
            scenario: Текущий сценарий
            feedback: Фидбек/пожелания по изменению
            
        Returns:
            Обновленный JSON сценария
        """
        user_prompt = f"""Вот текущий сценарий:

```json
{json.dumps(scenario, indent=2, ensure_ascii=False)}
```

Внеси изменения согласно фидбеку: {feedback}

Верни ТОЛЬКО JSON без markdown, без пояснений, только валидный JSON."""
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        response = self.client.generate(messages)
        
        # Извлечение JSON
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
        if response.endswith("```"):
            response = response.rsplit("\n", 1)[0]
        response = response.strip()
        
        if response.startswith("```json"):
            response = response[7:].strip()
        
        try:
            refined = json.loads(response)
            return refined
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ модели:\n{response}")
            raise
    
    def generate_image_prompts_only(self, scenario: dict) -> list:
        """
        Извлечение только промптов для изображений из сценария
        
        Args:
            scenario: JSON сценария
            
        Returns:
            Список промптов
        """
        prompts = []
        for scene in scenario.get("scenes", []):
            prompts.append({
                "scene": scene.get("scene_number"),
                "prompt": scene.get("image_prompt"),
                "duration": scene.get("duration_sec"),
                "voiceover": scene.get("voiceover_text"),
            })
        return prompts
    
    def save_scenario(self, scenario: dict, filepath: str):
        """Сохранение сценария в файл"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)
        print(f"✅ Сценарий сохранён: {filepath}")
    
    def load_scenario(self, filepath: str) -> dict:
        """Загрузка сценария из файла"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def print_scenario(self, scenario: dict):
        """Красивый вывод сценария"""
        print("\n" + "="*60)
        print(f"🎬 {scenario.get('title', 'Без названия')}")
        print("="*60)
        print(f"📝 {scenario.get('description', '')}")
        print(f"⏱️  Общая длительность: {scenario.get('total_duration_sec')} сек")
        print("="*60)
        
        for scene in scenario.get("scenes", []):
            print(f"\n🎞️  Сцена {scene.get('scene_number')}")
            print(f"   ⏰ Время: {scene.get('start_time_sec')}с - {scene.get('start_time_sec') + scene.get('duration_sec')}с ({scene.get('duration_sec')}с)")
            print(f"   🎙️  Озвучка: {scene.get('voiceover_text')}")
            print(f"   🎨 Промпт: {scene.get('image_prompt')}")
            print(f"   📐 Соотношение: {scene.get('image_aspect_ratio')}")
            print(f"   🎭 Настроение: {scene.get('mood')}")
            print(f"   🔀 Переход: {scene.get('transition')}")
        
        if scenario.get("notes"):
            print(f"\n📌 Заметки: {scenario.get('notes')}")
        print("="*60 + "\n")


def create_scenario_cli():
    """CLI для создания сценария"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Генератор видео-сценариев через Fireworks AI")
    parser.add_argument("topic", nargs="?", help="Тема видео")
    parser.add_argument("--api-key", help="Fireworks API key")
    parser.add_argument("--language", "-l", default="ru", help="Язык озвучки (ru, en)")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Целевая длительность (сек)")
    parser.add_argument("--style", "-s", help="Стиль видео")
    parser.add_argument("--scenes", "-n", type=int, help="Количество сцен")
    parser.add_argument("--output", "-o", help="Файл для сохранения сценария (JSON)")
    parser.add_argument("--refine", "-r", help="Файл сценария для доработки")
    parser.add_argument("--feedback", "-f", help="Фидбек для доработки сценария")
    
    args = parser.parse_args()
    
    # Определение темы
    topic = args.topic
    if not topic:
        topic = input("🎬 Введите тему видео: ").strip()
        if not topic:
            print("❌ Тема не может быть пустой")
            return
    
    planner = VideoScenarioPlanner(api_key=args.api_key)
    
    # Доработка существующего сценария
    if args.refine and args.feedback:
        print(f"📝 Доработка сценария: {args.refine}")
        scenario = planner.load_scenario(args.refine)
        scenario = planner.refine_scenario(scenario, args.feedback)
    else:
        # Создание нового сценария
        print(f"🎬 Создание сценария: {topic}")
        scenario = planner.create_scenario(
            topic=topic,
            language=args.language,
            target_duration=args.duration,
            style=args.style,
            num_scenes=args.scenes,
        )
    
    # Вывод и сохранение
    planner.print_scenario(scenario)
    
    output_file = args.output or f"scenario_{topic[:30].replace(' ', '_')}.json"
    planner.save_scenario(scenario, output_file)


if __name__ == "__main__":
    create_scenario_cli()

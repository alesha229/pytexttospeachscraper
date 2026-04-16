"""
Video Scenario Planner V3 - Unit-Based
=======================================
Генерирует сценарий в формате переиспользуемых юнитов:
- Цитаты/новости (с веб-поиском)
- Персоны (с поиском фото)
- Тезисы (plain text для экрана)
- Объекты/локации (фото со стока)

Использование:
    python video_scenario_planner_v3.py "Тема видео"
    python video_scenario_planner_v3.py "Тема" --language en --duration 60

Вход:
    - topic (str): Тема видео
    - language (str): Язык (ru, en)
    - duration (int): Длительность в секундах
    - style (str): Стиль (cinematic, documentary, etc)

Выход:
    - JSON сценария с units_manifest для переиспользования
"""

import json
import os
from typing import Optional, List, Dict
from openai import OpenAI

CONFIG = {
    "api_key": "fw_RHz4x8ZwqbsvKhyp1qkpR6",
    "model": "accounts/fireworks/models/qwen3p6-plus",
    "temperature": 0.7,
    "max_tokens": 8192,
    "default_language": "ru",
}


class FireworksClient:
    """Клиент для Fireworks AI"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["api_key"] or os.environ.get("FIREWORKS_API_KEY")
        if not self.api_key:
            raise ValueError("API ключ не указан")
        
        self.client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self.api_key,
        )
    
    def generate(self, messages: list, model: str = None, temperature: float = None, max_tokens: int = None) -> str:
        use_stream = max_tokens and max_tokens > 4000
        
        try:
            response = self.client.chat.completions.create(
                model=model or CONFIG["model"],
                messages=messages,
                temperature=temperature or CONFIG["temperature"],
                max_tokens=max_tokens or CONFIG["max_tokens"],
                stream=use_stream,
            )
            
            if use_stream:
                full_response = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                return full_response
            else:
                return response.choices[0].message.content or ""
        except Exception as e:
            raise Exception(f"Ошибка LLM: {e}")


class VideoScenarioPlannerV3:
    """
    Планировщик сценария V3 - на основе переиспользуемых юнитов
    
    Структура:
    - units_manifest: список всех сущностей (цитаты, персоны, объекты)
    - timeline: последовательность ссылок на юниты + тайминги
    """
    
    SYSTEM_PROMPT = """Ты — Режиссер документального YouTube-канала. Твоя задача: создать сценарий из ПЕРЕИСПОЛЬЗУЕМЫХ ЮНИТОВ.

### КОНЦЕПЦИЯ ЮНИТОВ:
Вместо генерации текста для каждой сцены, ты создаешь БАЗУ ЗНАНИЙ (units_manifest), которую можно переиспользовать в разных видео.

### ТИПЫ ЮНИТОВ:

1. **quote** - Цитата или факт
   - content: Текст цитаты (1-2 предложения)
   - source: Источник (имя человека, сайт, новость)
   - search_query: Запрос для поиска оригинала в интернете
   - verified: true если есть подтверждение источника

2. **person** - Реальный человек
   - name: Полное имя
   - role: Роль/профессия
   - search_query: Запрос для поиска фото (например: "Victor Surge Slenderman creator")
   - description: Краткое описание для контекста

3. **thesis** - Тезис для экрана (plain text)
   - content: Короткий текст (2-5 слов) для вывода на экран
   - emphasis: уровень важности (high/medium/low)
   - display_duration: сколько секунд показывать (3-8)

4. **object** - Объект или локация
   - name: Название
   - type: object/location/concept
   - search_query: Запрос для стокового фото
   - description: Описание для генерации

5. **news_item** - Новость из интернета
   - headline: Заголовок
   - source: Сайт/издание
   - url: Ссылка (если есть)
   - summary: Краткое содержание (1-2 предложения)
   - search_query: Запрос для проверки

### СТРУКТУРА JSON:

{
    "metadata": {
        "title": "Название видео",
        "vibe": "Стиль (mystery/documentary/dramatic)",
        "tempo": "Темп (slow/medium/fast)",
        "total_duration": 60
    },
    "units_manifest": [
        {
            "id": "quote_1",
            "type": "quote",
            "content": "Я создал его как шутку, но он стал реальностью",
            "source": "Victor Surge",
            "search_query": "Victor Surge Slenderman quote 2009",
            "verified": true
        },
        {
            "id": "person_1", 
            "type": "person",
            "name": "Victor Surge",
            "role": "Создатель Слендермена",
            "search_query": "Victor Surge Eric Knudsen photo",
            "description": "Художник и фотограф, создал Слендермена в 2009"
        },
        {
            "id": "thesis_1",
            "type": "thesis",
            "content": "ИЗ ШУТКИ В РЕАЛЬНОСТЬ",
            "emphasis": "high",
            "display_duration": 5
        },
        {
            "id": "object_1",
            "type": "object",
            "name": "Slenderman",
            "search_query": "Slenderman tall faceless suit forest",
            "description": "Высокая фигура в черном костюме без лица"
        }
    ],
    "timeline": [
        {
            "start_time": 0,
            "end_time": 15,
            "duration": 15,
            "voiceover": "Текст озвучки для этой сцены...",
            "units": [
                {"ref": "quote_1", "role": "main_quote"},
                {"ref": "thesis_1", "role": "screen_text"},
                {"ref": "person_1", "role": "person_photo"},
                {"ref": "object_1", "role": "background"}
            ],
            "background_prompt": "Описание фона для генерации/поиска"
        }
    ]
}

### ПРАВИЛА:
1. Каждый юнит должен быть УНИВЕРСАЛЬНЫМ - его можно использовать в других видео
2. search_query должен быть КОНКРЕТНЫМ для точного поиска
3. thesis - только короткие фразы 2-5 слов
4. quote - реальные цитаты с указанием источника
5. timeline ссылается на юниты по id, не дублирует контент

### ВАЖНО:
- Не создавай юниты "на лету" - только те, что есть в manifest
- В voiceover используй естественный разговорный язык
- Распределяй юниты по сценам логически

Верни ТОЛЬКО JSON без markdown."""

    def __init__(self, api_key: str = None):
        self.client = FireworksClient(api_key)
    
    def create_scenario(
        self,
        topic: str,
        language: str = None,
        duration: int = 60,
        style: str = None,
        num_scenes: int = None
    ) -> dict:
        """Создает сценарий с units_manifest"""
        
        lang = language or CONFIG["default_language"]
        estimated_words = int(duration * 2.5)
        
        user_prompt = f"""Создай сценарий с переиспользуемыми юнитами.

ТЕМА: {topic}
ЯЗЫК: {lang}
ДЛИТЕЛЬНОСТЬ: {duration} сек (~{estimated_words} слов озвучки)"""
        
        if style:
            user_prompt += f"\nСТИЛЬ: {style}"
        if num_scenes:
            user_prompt += f"\nСЦЕН: {num_scenes}"
        
        user_prompt += f"""

ТРЕБОВАНИЯ:
- Общий объем voiceover: ~{estimated_words} слов
- Создай 8-15 юнитов в manifest (цитаты, персоны, тезисы, объекты)
- Каждая сцена использует 2-4 юнита
- search_query должен быть на английском для лучшего поиска

Верни ТОЛЬКО JSON."""
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        response = self.client.generate(messages, max_tokens=8192)
        response = response.strip()
        
        # Убираем markdown
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
        if response.endswith("```"):
            response = response.rsplit("\n", 1)[0]
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:].strip()
        
        try:
            scenario = json.loads(response)
            return scenario
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ (первые 500 символов):\n{response[:500]}...")
            
            # Пытаемся извлечь JSON
            json_start = response.find("{")
            json_end = response.rfind("}")
            if json_start != -1 and json_end != -1:
                try:
                    return json.loads(response[json_start:json_end+1])
                except:
                    pass
            raise ValueError("Не удалось получить валидный JSON")
    
    def save_scenario(self, scenario: dict, filepath: str):
        """Сохраняет сценарий"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)
        print(f"✅ Сценарий сохранён: {filepath}")
    
    def print_scenario(self, scenario: dict):
        """Выводит сценарий"""
        print("\n" + "="*60)
        meta = scenario.get("metadata", {})
        print(f"🎬 {meta.get('title', 'Без названия')}")
        print(f"📝 Стиль: {meta.get('vibe', '')} | Темп: {meta.get('tempo', '')}")
        print("="*60)
        
        # Юниты
        units = scenario.get("units_manifest", [])
        print(f"\n📦 ЮНИТЫ ({len(units)}):")
        for unit in units:
            unit_type = unit.get("type", "")
            unit_id = unit.get("id", "")
            
            if unit_type == "quote":
                print(f"  💬 [{unit_id}] \"{unit.get('content', '')[:50]}...\" — {unit.get('source', '')}")
            elif unit_type == "person":
                print(f"  👤 [{unit_id}] {unit.get('name', '')} — {unit.get('role', '')}")
            elif unit_type == "thesis":
                print(f"  📌 [{unit_id}] {unit.get('content', '')} ({unit.get('emphasis', '')})")
            elif unit_type == "object":
                print(f"  🎯 [{unit_id}] {unit.get('name', '')} — {unit.get('type', '')}")
            elif unit_type == "news_item":
                print(f"  📰 [{unit_id}] {unit.get('headline', '')}")
        
        # Таймлайн
        timeline = scenario.get("timeline", [])
        print(f"\n🎞️ ТАЙМЛАЙН ({len(timeline)} сцен):")
        for i, block in enumerate(timeline):
            units_refs = block.get("units", [])
            print(f"  [{i+1}] {block.get('start_time', 0):.0f}s-{block.get('end_time', 0):.0f}s")
            print(f"      🎙️ {block.get('voiceover', '')[:80]}...")
            if units_refs:
                print(f"      🔗 Юниты: {', '.join(u.get('ref', '') for u in units_refs)}")
        
        print("="*60 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Генератор сценариев V3 (unit-based)")
    parser.add_argument("topic", nargs="?", help="Тема видео")
    parser.add_argument("--api-key", help="Fireworks API key")
    parser.add_argument("--language", "-l", default="ru", help="Язык")
    parser.add_argument("--duration", "-d", type=int, default=60, help="Длительность (сек)")
    parser.add_argument("--style", "-s", help="Стиль")
    parser.add_argument("--scenes", "-n", type=int, help="Количество сцен")
    parser.add_argument("--output", "-o", help="Файл вывода")
    
    args = parser.parse_args()
    
    topic = args.topic
    if not topic:
        topic = input("🎬 Введите тему: ").strip()
        if not topic:
            print("❌ Тема не может быть пустой")
            return
    
    planner = VideoScenarioPlannerV3(api_key=args.api_key)
    
    scenario = planner.create_scenario(
        topic=topic,
        language=args.language,
        duration=args.duration,
        style=args.style,
        num_scenes=args.scenes,
    )
    
    planner.print_scenario(scenario)
    
    output_file = args.output or f"scenario_v3_{topic[:30].replace(' ', '_')}.json"
    planner.save_scenario(scenario, output_file)


if __name__ == "__main__":
    main()

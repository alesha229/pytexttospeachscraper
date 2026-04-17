"""
Примеры использования tts_engine как модуля
"""

from tts_engine import tts, tts_single, tts_batch, list_voices, split_text_smart

# ======================== ПРИМЕР 1: Простая генерация ========================

def example_simple():
    """Генерация короткого текста"""
    success = tts(
        text="Привет! Это тестовый текст.",
        voice_id="Svetlana",
        output_path="output/simple.wav"
    )
    if success:
        print("✅ Готово!")

# ======================== ПРИМЕР 2: Batch-генерация ========================

def example_batch():
    """Генерация большого текста с авто-разбиением"""
    with open("book_chapter.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    success = tts(
        text=text,
        voice_id="Dmitry",
        output_path="output_batch/chapter.wav",
        max_chunk=1000,  # можно изменить размер фрагмента
        on_progress=lambda msg: print(f"  Прогресс: {msg}")
    )
    
    if success:
        print("✅ Книга озвучена!")

# ======================== ПРИМЕР 3: Ручное разбиение ========================

def example_manual_split():
    """Ручное управление разбиением"""
    text = "Очень длинный текст..."
    chunks = split_text_smart(text, max_length=500)  # по 500 символов
    
    print(f"Текст разбит на {len(chunks)} частей")
    for i, chunk in enumerate(chunks):
        tts_single(
            text=chunk,
            voice_id="Nikolai",
            output_path=f"output/part_{i:03d}.wav"
        )

# ======================== ПРИМЕР 4: Список голосов ========================

def example_list_voices():
    """Получение списка голосов программно"""
    from tts_engine import load_voices
    
    voices = load_voices()
    russian = [v for v in voices if "ru" in v.languages]
    
    for v in russian:
        print(f"{v.display_name}: {v.description}")

# ======================== ПРИМЕР 5: Callback прогресс ========================

def example_with_progress():
    """Генерация с callback для UI"""
    def progress_handler(message):
        # Здесь можно обновлять прогресс-бар в GUI
        print(f"[PROGRESS] {message}")
    
    tts(
        text="Длинный текст для демонстрации прогресса...",
        voice_id="Elena",
        output_path="output/with_progress.wav",
        on_progress=progress_handler
    )

# ======================== ЗАПУСК ========================

if __name__ == "__main__":
    print("Пример 1: Простая генерация")
    example_simple()
    
    print("\nПример 4: Список голосов")
    example_list_voices()

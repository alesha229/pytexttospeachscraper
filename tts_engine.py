"""
InWorld TTS Engine
==================
Модуль для преобразования текста в речь через InWorld API.
Поддерживает batch-обработку больших файлов с умным разбиением текста.

Использование:
    python tts_engine.py --text "Привет мир" --voice Elena --output out.wav
    python tts_engine.py --file input.txt --voice Dmitry --output out.wav
    python tts_engine.py --list-voices
    python tts_engine.py --list-voices --lang-filter ru

Вход:
    - text (str): Текст для озвучки (или --file)
    - voice (str): ID голоса или display name из voices.json (например, "Elena", "Dmitry")
    - output (str): Путь к выходному WAV файлу
    - max-chars (int): Максимум символов на фрагмент (по умолчанию 1000)

Выход:
    - output (str): WAV файл с аудио

Доступные русские голоса:
    - Elena: Clear, mid-range female voice
    - Dmitry: Deep, gravelly male voice
    - Nikolai: Deep, resonant male voice
    - Svetlana: Soft, high-pitched female voice
"""

import requests
import json
import base64
import struct
import os
import re
import wave
import argparse
import sys
from typing import List, Optional, Callable
from dataclasses import dataclass

# Fix для Windows консоли
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# ======================== КОНФИГУРАЦИЯ ========================

URL = "https://inworld.ai/api/create-speech"

COOKIES = {
    "inworld_uid": os.environ.get("INWORLD_UID", "b9ac5a4c-a0fd-493a-9e07-930fc1ac3db1"),
}

HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}

MAX_CHARS = 1000
SAMPLE_RATE = 48000

# Папки по умолчанию
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
BATCH_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_batch")
VOICES_FILE = os.path.join(SCRIPT_DIR, "voices.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(BATCH_OUTPUT_DIR, exist_ok=True)


# ======================== ДАННЫЕ ========================

@dataclass
class VoiceInfo:
    """Информация о голосе"""
    voice_id: str
    display_name: str
    languages: List[str]
    description: str = ""


# ======================== ЗАГРУЗКА ГОЛОСОВ ========================

def load_voices(voices_file: str = None) -> List[VoiceInfo]:
    """Загружает список голосов из voices.json"""
    if voices_file is None:
        voices_file = VOICES_FILE
    
    try:
        with open(voices_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        voices = []
        for v in data.get("voices", []):
            voices.append(VoiceInfo(
                voice_id=v["voiceId"],
                display_name=v["displayName"],
                languages=v.get("languages", []),
                description=v.get("description", "")
            ))
        return voices
    except Exception as e:
        print(f"⚠ Не удалось загрузить голоса: {e}", file=sys.stderr)
        return []


def get_voice_map(voices_file: str = None) -> dict:
    """Возвращает словарь {display_name: voice_id}"""
    voices = load_voices(voices_file)
    return {v.display_name: v.voice_id for v in voices}


def list_voices(voices_file: str = None, lang_filter: str = None):
    """Выводит список доступных голосов"""
    voices = load_voices(voices_file)
    
    if not voices:
        print("⚠ Голоса не найдены. Проверьте voices.json")
        return
    
    print(f"\n🎙️ Доступные голоса ({len(voices)}):")
    print("=" * 70)
    
    for v in voices:
        lang_str = ", ".join(v.languages)
        if lang_filter and lang_filter.lower() not in lang_str.lower():
            continue
        
        print(f"\n  📌 {v.display_name}")
        print(f"     Языки: {lang_str}")
        if v.description:
            desc = v.description[:100] + "..." if len(v.description) > 100 else v.description
            print(f"     Описание: {desc}")
    
    print("\n" + "=" * 70)


# ======================== УТИЛИТЫ ТЕКСТА ========================

def split_text_smart(text: str, max_length: int = MAX_CHARS) -> List[str]:
    """
    Разбивает текст на части по max_length символов.
    Не обрывает слова или предложения на полуслове.
    
    Приоритет разбиения:
    1. Двойной перенос строки
    2. Перенос строки
    3. Точка / ! / ?
    4. Точка с запятой / двоеточие
    5. Запятая
    6. Пробел
    7. Жёсткий лимит
    """
    if len(text) <= max_length:
        return [text.strip()]
    
    chunks = []
    remaining = text
    
    while len(remaining) > max_length:
        segment = remaining[:max_length]
        split_pos = None
        
        # 1. Двойной перенос строки
        last_double_newline = segment.rfind('\n\n')
        if last_double_newline > max_length * 0.3:
            split_pos = last_double_newline + 2
        
        # 2. Перенос строки
        if split_pos is None:
            last_newline = segment.rfind('\n')
            if last_newline > max_length * 0.3:
                split_pos = last_newline + 1
        
        # 3. Конец предложения
        if split_pos is None:
            for match in re.finditer(r'[.!?]["\']?\s', segment):
                pos = match.end()
                if pos > max_length * 0.3:
                    split_pos = pos
        
        # 4. ; :
        if split_pos is None:
            for match in re.finditer(r'[;:]\s', segment):
                pos = match.end()
                if pos > max_length * 0.3:
                    split_pos = pos
        
        # 5. Запятая
        if split_pos is None:
            last_comma = segment.rfind(',')
            if last_comma > max_length * 0.3:
                split_pos = last_comma + 1
        
        # 6. Пробел
        if split_pos is None:
            last_space = segment.rfind(' ')
            if last_space > max_length * 0.3:
                split_pos = last_space + 1
        
        # 7. Жёсткий лимит
        if split_pos is None:
            split_pos = max_length
        
        chunk = remaining[:split_pos].strip()
        if chunk:
            chunks.append(chunk)
        
        remaining = remaining[split_pos:].strip()
    
    if remaining.strip():
        chunks.append(remaining.strip())
    
    return chunks


def create_wav_header(sample_rate: int, data_size: int) -> bytes:
    """Генерирует заголовок WAV файла (44 байта)"""
    n_channels = 1
    sample_width = 2
    
    header = b'RIFF'
    header += struct.pack('<I', data_size + 36)
    header += b'WAVEfmt '
    header += struct.pack('<I', 16)
    header += struct.pack('<H', 1)
    header += struct.pack('<H', n_channels)
    header += struct.pack('<I', sample_rate)
    header += struct.pack('<I', sample_rate * n_channels * sample_width)
    header += struct.pack('<H', n_channels * sample_width)
    header += struct.pack('<H', 8 * sample_width)
    header += b'data'
    header += struct.pack('<I', data_size)
    return header


def merge_wav_files(file_paths: List[str], output_path: str) -> bool:
    """Объединяет несколько WAV файлов в один"""
    if not file_paths:
        return False
    
    try:
        audio_data = b''
        sample_rate = SAMPLE_RATE
        n_channels = 1
        sample_width = 2
        
        for fpath in file_paths:
            if not os.path.exists(fpath):
                continue
            try:
                with wave.open(fpath, 'rb') as wf:
                    sample_rate = wf.getframerate()
                    n_channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                    audio_data += wf.readframes(wf.getnframes())
            except Exception:
                with open(fpath, 'rb') as f:
                    content = f.read()
                    if content.startswith(b'RIFF'):
                        audio_data += content[44:]
                    else:
                        audio_data += content
        
        if not audio_data:
            return False
        
        with wave.open(output_path, 'wb') as out_wf:
            out_wf.setnchannels(n_channels)
            out_wf.setsampwidth(sample_width)
            out_wf.setframerate(sample_rate)
            out_wf.writeframes(audio_data)
        
        return True
    except Exception as e:
        print(f"⚠ Ошибка при объединении WAV: {e}", file=sys.stderr)
        return False


# ======================== TTS ЯДРО ========================

def _fetch_audio_chunk(text: str, voice_id: str) -> Optional[bytes]:
    """
    Загружает аудио для одного запроса TTS.
    Возвращает сырые PCM данные (без заголовка WAV).
    """
    payload = {
        "text": text,
        "voiceId": voice_id,
        "modelId": "inworld-tts-1.5-max",
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": SAMPLE_RATE
        }
    }
    
    raw_audio_data = bytearray()
    
    response = requests.post(URL, headers=HEADERS, cookies=COOKIES, json=payload, stream=True, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"Ошибка сервера: {response.status_code}")
    
    for line in response.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line.decode('utf-8'))
            b64_audio = data.get("result", {}).get("audioContent") or data.get("audioContent")
            if b64_audio:
                chunk_bytes = base64.b64decode(b64_audio)
                # Убираем WAV заголовок если есть
                if chunk_bytes.startswith(b'RIFF'):
                    raw_audio_data.extend(chunk_bytes[44:])
                else:
                    raw_audio_data.extend(chunk_bytes)
            elif "error" in data:
                print(f"⚠ Ошибка от сервера: {data['error']}")
        except json.JSONDecodeError:
            continue
    
    if len(raw_audio_data) > 0:
        return bytes(raw_audio_data)
    else:
        return None


def save_wav(raw_audio: bytes, output_path: str, sample_rate: int = SAMPLE_RATE) -> bool:
    """Сохраняет сырые PCM данные в WAV файл"""
    try:
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_audio)
        return True
    except Exception as e:
        print(f"⚠ Ошибка сохранения WAV: {e}", file=sys.stderr)
        return False


# ======================== PUBLIC API ========================

def tts_single(text: str, voice_id: str, output_path: str, 
               on_progress: Callable[[str], None] = None) -> bool:
    """
    Генерирует аудио для одного текста.
    
    Args:
        text: Текст для озвучки
        voice_id: ID голоса
        output_path: Путь к выходному файлу
        on_progress: Callback для прогресса (str)
    
    Returns:
        True если успешно
    """
    def _status(msg):
        if on_progress:
            on_progress(msg)
        else:
            print(f"  {msg}")
    
    _status("Подключение к серверу...")
    raw_audio = _fetch_audio_chunk(text, voice_id)
    
    if raw_audio is None:
        return False
    
    _status(f"Сохранение: {len(raw_audio)} байт")
    return save_wav(raw_audio, output_path)


def tts_batch(text: str, voice_id: str, output_path: str,
              max_chunk: int = MAX_CHARS,
              on_progress: Callable[[str], None] = None) -> bool:
    """
    Генерирует аудио для большого текста с разбиением на части.
    Куски сохраняются в подпапку, основной файл — в основную папку.

    Args:
        text: Текст для озвучки
        voice_id: ID голоса
        output_path: Путь к выходному файлу
        max_chunk: Максимальный размер одного фрагмента
        on_progress: Callback для прогресса

    Returns:
        True если успешно
    """
    def _status(msg):
        if on_progress:
            on_progress(msg)
        else:
            print(f"  {msg}")

    chunks = split_text_smart(text, max_chunk)

    if len(chunks) == 1:
        # Маленький текст
        return tts_single(text, voice_id, output_path, on_progress)

    _status(f"📝 Текст разбит на {len(chunks)} частей")

    # Основная папка
    main_dir = os.path.dirname(output_path) or BATCH_OUTPUT_DIR
    base_name = os.path.splitext(os.path.basename(output_path))[0]

    # Подпапка для кусков
    chunks_dir = os.path.join(main_dir, f"{base_name}_parts")
    os.makedirs(chunks_dir, exist_ok=True)

    chunk_files = []

    try:
        for i, chunk in enumerate(chunks):
            chunk_filename = f"part{i+1:03d}.wav"
            chunk_path = os.path.join(chunks_dir, chunk_filename)
            chunk_files.append(chunk_path)

            _status(f"🎤 Генерация части {i+1}/{len(chunks)}...")

            raw_audio = _fetch_audio_chunk(chunk, voice_id)
            if raw_audio is None:
                _status(f"⚠ Не удалось получить аудио для части {i+1}")
                return False

            save_wav(raw_audio, chunk_path)

        # Объединяем
        _status("🔗 Объединение файлов...")
        if merge_wav_files(chunk_files, output_path):
            # Куски НЕ удаляем — сохраняем для переиспользования
            _status(f"✅ Готово! {len(chunks)} частей | Куски: {chunks_dir}")
            return True
        else:
            _status("⚠ Ошибка при объединении")
            return False

    except Exception as e:
        _status(f"❌ Ошибка: {e}")
        return False


def tts(text: str, voice_id: str, output_path: str,
        max_chunk: int = MAX_CHARS,
        on_progress: Callable[[str], None] = None) -> bool:
    """
    Универсальная функция TTS.
    Автоматически выбирает single или batch режим.
    """
    if len(text) > max_chunk:
        return tts_batch(text, voice_id, output_path, max_chunk, on_progress)
    else:
        return tts_single(text, voice_id, output_path, on_progress)


# ======================== CLI ========================

def cli():
    """Консольный интерфейс"""
    parser = argparse.ArgumentParser(
        description="InWorld TTS Engine — преобразование текста в речь",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python tts_engine.py --text "Привет мир" --voice "voice_id" --output out.wav
  python tts_engine.py --file input.txt --voice "voice_id" --output out.wav
  python tts_engine.py --list-voices
  python tts_engine.py --file book.txt --voice "voice_id" --output book.wav --batch-dir ./output
        """
    )
    
    # Входные данные
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text", "-t", help="Текст для озвучки")
    input_group.add_argument("--file", "-f", help="Путь к текстовому файлу")
    input_group.add_argument("--list-voices", "-l", action="store_true", help="Список голосов")
    
    # Настройки
    parser.add_argument("--voice", "-v", help="ID голоса или display name")
    parser.add_argument("--output", "-o", help="Путь к выходному WAV файлу")
    parser.add_argument("--max-chars", "-m", type=int, default=MAX_CHARS, 
                       help=f"Максимум символов на фрагмент (по умолчанию: {MAX_CHARS})")
    parser.add_argument("--output-dir", "-d", 
                       help=f"Папка для выходных файлов (по умолчанию: output/)")
    parser.add_argument("--batch-dir", 
                       help=f"Папка для batch файлов (по умолчанию: output_batch/)")
    parser.add_argument("--lang-filter", 
                       help="Фильтр языков при --list-voices (например: ru, en)")
    
    args = parser.parse_args()
    
    # Список голосов
    if args.list_voices:
        list_voices(lang_filter=args.lang_filter)
        return
    
    # Проверка голоса
    if not args.voice:
        print("⚠ Укажите голос через --voice", file=sys.stderr)
        sys.exit(1)
    
    # Определяем голос
    voice_map = get_voice_map()
    voice_id = voice_map.get(args.voice, args.voice)
    
    # Загружаем текст
    if args.file:
        if not os.path.exists(args.file):
            print(f"⚠ Файл не найден: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"📄 Загружен файл: {args.file} ({len(text)} символов)")
    else:
        text = args.text
    
    # Определяем выходной путь
    if args.output:
        output_path = args.output
    else:
        # Генерируем имя файла
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in text[:30]).strip()
        if not safe_name:
            safe_name = "audio"
        
        is_batch = len(text) > args.max_chars
        output_dir = args.output_dir or (BATCH_OUTPUT_DIR if is_batch else OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        
        suffix = "_batch" if is_batch else ""
        filename = f"{safe_name}{suffix}.wav"
        output_path = os.path.join(output_dir, filename)
    
    # Информация
    chunks = split_text_smart(text, args.max_chars)
    print(f"\n🎙️ Голос: {args.voice}")
    print(f"📝 Символов: {len(text)}")
    print(f"📑 Фрагментов: {len(chunks)}")
    print(f"📂 Выход: {output_path}")
    print(f"{'━' * 50}")
    
    # Генерация
    success = tts(
        text=text,
        voice_id=voice_id,
        output_path=output_path,
        max_chunk=args.max_chars
    )
    
    if success:
        print(f"\n✅ Готово! Файл: {output_path}")
    else:
        print(f"\n❌ Ошибка генерации!")
        sys.exit(1)


if __name__ == "__main__":
    cli()

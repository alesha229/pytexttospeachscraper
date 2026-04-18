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

from ..config import INWORLD_UID, TTS_SAMPLE_RATE, TTS_MAX_CHARS, TTS_DEFAULT_VOICE_ID, TTS_MODEL_ID

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


URL = "https://inworld.ai/api/create-speech"

COOKIES = {
    "inworld_uid": INWORLD_UID,
}

HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}

MAX_CHARS = TTS_MAX_CHARS
SAMPLE_RATE = TTS_SAMPLE_RATE

APP_DIR = os.path.dirname(os.path.abspath(__file__))
VOICES_FILE = os.path.join(os.path.dirname(APP_DIR), "data", "voices.json")


@dataclass
class VoiceInfo:
    voice_id: str
    display_name: str
    languages: List[str]
    description: str = ""


def load_voices(voices_file: str = None) -> List[VoiceInfo]:
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
        print(f"Failed to load voices: {e}", file=sys.stderr)
        return []


def get_voice_map(voices_file: str = None) -> dict:
    return {v.display_name: v.voice_id for v in load_voices(voices_file)}


def list_voices(voices_file: str = None, lang_filter: str = None):
    voices = load_voices(voices_file)
    if not voices:
        print("No voices found. Check voices.json")
        return
    print(f"\nAvailable voices ({len(voices)}):")
    print("=" * 70)
    for v in voices:
        lang_str = ", ".join(v.languages)
        if lang_filter and lang_filter.lower() not in lang_str.lower():
            continue
        print(f"\n  {v.display_name}")
        print(f"     Languages: {lang_str}")
        if v.description:
            desc = v.description[:100] + "..." if len(v.description) > 100 else v.description
            print(f"     Description: {desc}")
    print("\n" + "=" * 70)


def split_text_smart(text: str, max_length: int = MAX_CHARS) -> List[str]:
    if len(text) <= max_length:
        return [text.strip()]

    chunks = []
    remaining = text

    while len(remaining) > max_length:
        segment = remaining[:max_length]
        split_pos = None

        last_double_newline = segment.rfind('\n\n')
        if last_double_newline > max_length * 0.3:
            split_pos = last_double_newline + 2

        if split_pos is None:
            last_newline = segment.rfind('\n')
            if last_newline > max_length * 0.3:
                split_pos = last_newline + 1

        if split_pos is None:
            for match in re.finditer(r'[.!?]["\']?\s', segment):
                pos = match.end()
                if pos > max_length * 0.3:
                    split_pos = pos

        if split_pos is None:
            for match in re.finditer(r'[;:]\s', segment):
                pos = match.end()
                if pos > max_length * 0.3:
                    split_pos = pos

        if split_pos is None:
            last_comma = segment.rfind(',')
            if last_comma > max_length * 0.3:
                split_pos = last_comma + 1

        if split_pos is None:
            last_space = segment.rfind(' ')
            if last_space > max_length * 0.3:
                split_pos = last_space + 1

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
        print(f"WAV merge error: {e}", file=sys.stderr)
        return False


def _fetch_audio_chunk(text: str, voice_id: str) -> Optional[bytes]:
    payload = {
        "text": text,
        "voiceId": voice_id,
        "modelId": TTS_MODEL_ID,
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": SAMPLE_RATE
        }
    }

    raw_audio_data = bytearray()

    response = requests.post(URL, headers=HEADERS, cookies=COOKIES, json=payload, stream=True, timeout=60)

    if response.status_code != 200:
        raise Exception(f"Server error: {response.status_code}")

    for line in response.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line.decode('utf-8'))
            b64_audio = data.get("result", {}).get("audioContent") or data.get("audioContent")
            if b64_audio:
                chunk_bytes = base64.b64decode(b64_audio)
                if chunk_bytes.startswith(b'RIFF'):
                    raw_audio_data.extend(chunk_bytes[44:])
                else:
                    raw_audio_data.extend(chunk_bytes)
            elif "error" in data:
                print(f"Server error: {data['error']}")
        except json.JSONDecodeError:
            continue

    if len(raw_audio_data) > 0:
        return bytes(raw_audio_data)
    else:
        return None


def save_wav(raw_audio: bytes, output_path: str, sample_rate: int = SAMPLE_RATE) -> bool:
    try:
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_audio)
        return True
    except Exception as e:
        print(f"WAV save error: {e}", file=sys.stderr)
        return False


def tts_single(text: str, voice_id: str, output_path: str,
               on_progress: Callable[[str], None] = None) -> bool:
    def _status(msg):
        if on_progress:
            on_progress(msg)
        else:
            print(f"  {msg}")

    _status("Connecting...")
    raw_audio = _fetch_audio_chunk(text, voice_id)
    if raw_audio is None:
        return False
    _status(f"Saving: {len(raw_audio)} bytes")
    return save_wav(raw_audio, output_path)


def tts_batch(text: str, voice_id: str, output_path: str,
              max_chunk: int = MAX_CHARS,
              on_progress: Callable[[str], None] = None) -> bool:
    def _status(msg):
        if on_progress:
            on_progress(msg)
        else:
            print(f"  {msg}")

    chunks = split_text_smart(text, max_chunk)
    if len(chunks) == 1:
        return tts_single(text, voice_id, output_path, on_progress)

    _status(f"Text split into {len(chunks)} parts")

    main_dir = os.path.dirname(output_path) or "."
    base_name = os.path.splitext(os.path.basename(output_path))[0]
    chunks_dir = os.path.join(main_dir, f"{base_name}_parts")
    os.makedirs(chunks_dir, exist_ok=True)

    chunk_files = []

    try:
        for i, chunk in enumerate(chunks):
            chunk_filename = f"part{i + 1:03d}.wav"
            chunk_path = os.path.join(chunks_dir, chunk_filename)
            chunk_files.append(chunk_path)

            _status(f"Generating part {i + 1}/{len(chunks)}...")
            raw_audio = _fetch_audio_chunk(chunk, voice_id)
            if raw_audio is None:
                _status(f"Failed for part {i + 1}")
                return False
            save_wav(raw_audio, chunk_path)

        _status("Merging...")
        if merge_wav_files(chunk_files, output_path):
            _status(f"Done! {len(chunks)} parts | Chunks: {chunks_dir}")
            return True
        else:
            _status("Merge failed")
            return False
    except Exception as e:
        _status(f"Error: {e}")
        return False


def tts(text: str, voice_id: str, output_path: str,
        max_chunk: int = MAX_CHARS,
        on_progress: Callable[[str], None] = None) -> bool:
    if len(text) > max_chunk:
        return tts_batch(text, voice_id, output_path, max_chunk, on_progress)
    else:
        return tts_single(text, voice_id, output_path, on_progress)


def create_silence(duration: float, output_path: str) -> str:
    num_samples = int(duration * SAMPLE_RATE)
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b'\x00\x00' * num_samples)
    return output_path

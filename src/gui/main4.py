import requests
import json
import base64
import struct
import os
import threading
import ctypes
from ctypes import wintypes
import pygame
import re
import wave
import io

# Используем tkinterdnd2 для drag-and-drop
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_TKDND = True
except ImportError:
    HAS_TKDND = False
    import tkinter as tk

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Настройки
URL = "https://inworld.ai/api/create-speech"

# Папка output рядом со скриптом
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Папка для больших файлов (batch)
BATCH_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_batch")
os.makedirs(BATCH_OUTPUT_DIR, exist_ok=True)

# Загрузка голосов из файла
VOICES_FILE = os.path.join(SCRIPT_DIR, "voices.json")

def load_voices():
    """Загружает список голосов из voices.json"""
    try:
        with open(VOICES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("voices", [])
    except Exception as e:
        print(f"Не удалось загрузить голоса: {e}")
        return []

ALL_VOICES = load_voices()
# Для выпадающего списка — "displayName (lang)", для payload — voiceId
VOICE_DISPLAY = []
VOICE_MAP = {}       # displayName → voiceId
VOICE_LANG_MAP = {}  # displayName → languages
for v in ALL_VOICES:
    name = v["displayName"]
    langs = ", ".join(v.get("languages", []))
    VOICE_DISPLAY.append(f"{name} ({langs})")
    VOICE_MAP[name] = v["voiceId"]
    VOICE_LANG_MAP[name] = langs

COOKIES = {
    "inworld_uid": "b9ac5a4c-a0fd-493a-9e07-930fc1ac3db1",
}

HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
}

MAX_CHARS = 1000

# Цветовая схема
COLORS = {
    "bg": "#0f0f23",
    "bg_secondary": "#1a1a2e",
    "bg_tertiary": "#16213e",
    "accent": "#6c63ff",
    "accent_hover": "#5a52d5",
    "accent_light": "#8b83ff",
    "text": "#e0e0e0",
    "text_secondary": "#a0a0b0",
    "text_muted": "#6a6a7a",
    "border": "#2a2a3e",
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "dropzone": "#1e3a5f",
    "dropzone_active": "#2a5298",
}


def split_text_smart(text, max_length=MAX_CHARS):
    """
    Разбивает текст на части по max_length символов.
    Не обрывает слова или предложения на полуслове.
    """
    if len(text) <= max_length:
        return [text]
    
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
        
        # 3. Точка, !, ? (конец предложения)
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
        
        # 7. Режем на max_length
        if split_pos is None:
            split_pos = max_length
        
        chunk = remaining[:split_pos].strip()
        if chunk:
            chunks.append(chunk)
        
        remaining = remaining[split_pos:].strip()
    
    if remaining.strip():
        chunks.append(remaining.strip())
    
    return chunks


def merge_wav_files(file_paths, output_path):
    """Объединяет несколько WAV файлов в один"""
    if not file_paths:
        return False
    
    try:
        audio_data = b''
        sample_rate = 48000
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
        print(f"Ошибка при объединении WAV: {e}")
        return False


def create_wav_header(sample_rate, data_size):
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


def run_tts(text, voice_id, output_path, status_callback, done_callback):
    """Выполняет TTS запрос в фоне"""
    payload = {
        "text": text,
        "voiceId": voice_id,
        "modelId": "inworld-tts-1.5-max",
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": 48000
        }
    }

    raw_audio_data = bytearray()

    try:
        status_callback("Подключение к серверу...")
        response = requests.post(URL, headers=HEADERS, cookies=COOKIES, json=payload, stream=True)

        if response.status_code != 200:
            done_callback(f"Ошибка сервера: {response.status_code}", False)
            return

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
                    status_callback(f"Загружено: {len(raw_audio_data)} байт")
            except Exception:
                continue

        if len(raw_audio_data) > 0:
            header = create_wav_header(48000, len(raw_audio_data))
            with open(output_path, "wb") as f:
                f.write(header)
                f.write(raw_audio_data)
            done_callback(f"Готово! Файл сохранён: {output_path}", True)
        else:
            done_callback("Данные не получены. Проверь куки!", False)

    except Exception as e:
        done_callback(f"Ошибка: {e}", False)


def run_batch_tts(text, voice_id, base_output_path, status_callback, done_callback):
    """
    Разбивает большой текст на части по MAX_CHARS символов,
    генерирует аудио для каждой части и объединяет в один файл.
    Куски сохраняются в подпапку, основной файл — в основную папку.
    """
    chunks = split_text_smart(text, MAX_CHARS)

    if len(chunks) == 1:
        # Если текст маленький, обрабатываем как обычный
        def simple_done(msg, success):
            done_callback(msg, success)
        run_tts(text, voice_id, base_output_path, status_callback, simple_done)
        return

    # Основная папка для выходного файла
    main_dir = os.path.dirname(base_output_path) or BATCH_OUTPUT_DIR
    base_name = os.path.splitext(os.path.basename(base_output_path))[0]

    # Создаём подпапку для кусков
    chunks_dir = os.path.join(main_dir, f"{base_name}_parts")
    os.makedirs(chunks_dir, exist_ok=True)

    chunk_files = []
    total_chunks = len(chunks)

    try:
        # Генерируем каждый чанк последовательно
        for i, chunk in enumerate(chunks):
            chunk_filename = f"part{i+1:03d}.wav"
            chunk_path = os.path.join(chunks_dir, chunk_filename)
            chunk_files.append(chunk_path)

            status_callback(f"Генерация части {i+1}/{total_chunks}...")

            payload = {
                "text": chunk,
                "voiceId": voice_id,
                "modelId": "inworld-tts-1.5-max",
                "audioConfig": {
                    "audioEncoding": "LINEAR16",
                    "sampleRateHertz": 48000
                }
            }

            raw_audio_data = bytearray()
            response = requests.post(URL, headers=HEADERS, cookies=COOKIES, json=payload, stream=True)

            if response.status_code != 200:
                done_callback(f"Ошибка сервера на части {i+1}: {response.status_code}", False)
                return

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
                except Exception:
                    continue

            if len(raw_audio_data) > 0:
                header = create_wav_header(48000, len(raw_audio_data))
                with open(chunk_path, "wb") as f:
                    f.write(header)
                    f.write(raw_audio_data)
            else:
                done_callback(f"Не удалось получить аудио для части {i+1}", False)
                return

        # Объединяем все части в основной файл
        status_callback("Объединение файлов...")
        if merge_wav_files(chunk_files, base_output_path):
            # Куски НЕ удаляем — сохраняем для возможного переиспользования
            done_callback(f"Готово! Файл: {base_output_path} | Куски: {chunks_dir} ({total_chunks} частей)", True)
        else:
            done_callback("Ошибка при объединении файлов", False)

    except Exception as e:
        done_callback(f"Ошибка: {e}", False)


class ModernButton(tk.Frame):
    """Современная кнопка с hover эффектами"""

    def __init__(self, master, text, command=None, icon=None, bg=None, fg=None,
                 hover_bg=None, font=("Segoe UI", 10), padding=(15, 8), **kwargs):
        super().__init__(master, bg=bg or COLORS["bg_secondary"], **kwargs)

        self._disabled = False
        self.original_bg = bg or COLORS["bg_secondary"]
        self.original_fg = fg or COLORS["text"]
        self.default_bg = self.original_bg
        self.default_fg = self.original_fg
        self.hover_color = hover_bg or COLORS["accent"]
        self.command = command

        self.button_frame = tk.Frame(self, bg=self.default_bg, cursor="hand2")
        self.button_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        btn_text = f"{icon} {text}" if icon else text
        self.label = tk.Label(
            self.button_frame,
            text=btn_text,
            bg=self.default_bg,
            fg=fg or COLORS["text"],
            font=font,
            cursor="hand2"
        )
        self.label.pack(fill=tk.BOTH, expand=True, padx=padding[0], pady=padding[1])

        for widget in (self, self.button_frame, self.label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, event=None):
        if self._disabled:
            return
        self.button_frame.config(bg=self.hover_color)
        self.label.config(bg=self.hover_color)
        super().config(bg=self.hover_color)

    def _on_leave(self, event=None):
        if self._disabled:
            return
        self.button_frame.config(bg=self.default_bg)
        self.label.config(bg=self.default_bg)
        super().config(bg=self.default_bg)

    def _on_click(self, event=None):
        if self.command and not self._disabled:
            self.command()

    def config(self, **kwargs):
        # Обрабатываем state
        if "state" in kwargs:
            self._disabled = (kwargs["state"] == tk.DISABLED)
            del kwargs["state"]

        # Обрабатываем bg
        if "bg" in kwargs:
            self.original_bg = kwargs["bg"]
            if not self._disabled:
                self.default_bg = kwargs["bg"]
            del kwargs["bg"]

        # Обрабатываем fg
        if "fg" in kwargs:
            self.original_fg = kwargs["fg"]
            if not self._disabled:
                self.default_fg = kwargs["fg"]
            del kwargs["fg"]

        # Вызываем родительский config без наших параметров
        if kwargs:
            super().config(**kwargs)

        # Обновляем внешний вид
        if hasattr(self, 'label'):
            if self._disabled:
                bg = COLORS["text_muted"]
                self.button_frame.config(bg=bg)
                self.label.config(bg=bg, fg=COLORS["text_muted"], cursor="arrow")
                super().config(bg=bg)
            else:
                self.button_frame.config(bg=self.default_bg)
                self.label.config(bg=self.default_bg, fg=self.default_fg, cursor="hand2")
                super().config(bg=self.default_bg)

    def set_text(self, text):
        """Обновляет текст кнопки"""
        if hasattr(self, 'label'):
            self.label.config(text=text)


class DarkDropdown(tk.Frame):
    """Кастомный выпадающий список с тёмной темой"""
    
    def __init__(self, master, values, variable, font=("Segoe UI", 10), **kwargs):
        super().__init__(master, bg=COLORS["bg_secondary"], **kwargs)
        
        # Получаем root window
        self.root = master.winfo_toplevel()
        
        self.values = values
        self.variable = variable
        self.font = font
        self.is_open = False
        self.dropdown = None
        self.listbox = None
        self.hovered_index = -1
        
        # Основной контейнер
        self.main_container = tk.Frame(self, bg=COLORS["bg_secondary"], cursor="hand2")
        self.main_container.pack(fill=tk.X, padx=0, pady=0)
        
        # Текст выбранного значения
        self.display_label = tk.Label(
            self.main_container,
            textvariable=variable,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            font=font,
            anchor=tk.W,
            padx=10,
            pady=8,
            cursor="hand2"
        )
        self.display_label.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        # Стрелка
        self.arrow_label = tk.Label(
            self.main_container,
            text="▼",
            bg=COLORS["bg_secondary"],
            fg=COLORS["accent"],
            font=("Segoe UI", 8),
            cursor="hand2",
            padx=10
        )
        self.arrow_label.pack(side=tk.RIGHT)
        
        # Граница
        self.config(highlightbackground=COLORS["border"], highlightthickness=1, relief=tk.FLAT)
        
        # Привязки событий
        for widget in (self, self.main_container, self.display_label, self.arrow_label):
            widget.bind("<Button-1>", self._toggle)
        
        self._update_display()
    
    def _update_display(self):
        """Обновляет отображаемый текст"""
        val = self.variable.get()
        self.display_label.config(text=val)
    
    def _toggle(self, event=None):
        """Открывает/закрывает dropdown"""
        if self.is_open:
            self._close()
        else:
            self._open()
    
    def _open(self):
        """Открывает выпадающий список"""
        self.is_open = True
        self.arrow_label.config(text="▲")
        self.config(highlightbackground=COLORS["accent"], highlightthickness=2)
        
        # Создаём Toplevel для списка
        self.dropdown = tk.Toplevel(self.root)
        self.dropdown.wm_overrideredirect(True)
        self.dropdown.attributes("-topmost", True)
        
        # Вычисляем позицию
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = self.winfo_width()
        
        # Максимальная высота — 250px, иначе по количеству элементов
        item_height = 28
        max_items = min(len(self.values), 8)
        height = item_height * max_items + 4
        
        self.dropdown.geometry(f"{width}x{height}+{x}+{y}")
        
        # Контейнер с прокруткой
        canvas_frame = tk.Frame(self.dropdown, bg=COLORS["bg_secondary"], relief=tk.FLAT)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Canvas + Scrollbar
        self.canvas = tk.Canvas(
            canvas_frame,
            bg=COLORS["bg_secondary"],
            highlightthickness=0,
            relief=tk.FLAT
        )
        scrollbar = tk.Scrollbar(
            canvas_frame,
            orient="vertical",
            command=self.canvas.yview,
            bg=COLORS["bg_tertiary"],
            troughcolor=COLORS["bg"],
            activebackground=COLORS["accent"],
            elementborderwidth=0,
            width=14
        )
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame для элементов внутри canvas
        items_frame = tk.Frame(self.canvas, bg=COLORS["bg_secondary"])
        self.canvas_window = self.canvas.create_window((0, 0), window=items_frame, anchor="nw")
        
        # Обновляем scrollregion после добавления элементов
        items_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )
        
        # Добавляем элементы
        self.item_frames = []
        for i, val in enumerate(self.values):
            item_frame = tk.Frame(items_frame, bg=COLORS["bg_secondary"], cursor="hand2")
            item_frame.pack(fill=tk.X, padx=2, pady=1)
            
            item_label = tk.Label(
                item_frame,
                text=val,
                bg=COLORS["bg_secondary"],
                fg=COLORS["text"],
                font=self.font,
                anchor=tk.W,
                padx=10,
                pady=6,
                cursor="hand2"
            )
            item_label.pack(fill=tk.BOTH, expand=True)
            
            # Привязки
            for w in (item_frame, item_label):
                w.bind("<Enter>", lambda e, idx=i: self._on_item_hover(idx))
                w.bind("<Leave>", lambda e, idx=i: self._on_item_leave(idx))
                w.bind("<Button-1>", lambda e, idx=i: self._on_item_click(idx))
            
            self.item_frames.append((item_frame, item_label))
        
        # Bind mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Bind click outside to close
        self.root.bind("<Button-1>", self._check_click_outside, add="+")
    
    def _close(self):
        """Закрывает выпадающий список"""
        self.is_open = False
        self.arrow_label.config(text="▼")
        self.config(highlightbackground=COLORS["border"], highlightthickness=1)
        self.hovered_index = -1
        
        if self.dropdown:
            self.canvas.unbind_all("<MouseWheel>")
            self.root.unbind("<Button-1>")
            self.dropdown.destroy()
            self.dropdown = None
    
    def _on_item_hover(self, index):
        """При наведении на элемент"""
        self.hovered_index = index
        for i, (frame, label) in enumerate(self.item_frames):
            if i == index:
                frame.config(bg=COLORS["accent"])
                label.config(bg=COLORS["accent"], fg="#ffffff")
            else:
                frame.config(bg=COLORS["bg_secondary"])
                label.config(bg=COLORS["bg_secondary"], fg=COLORS["text"])
    
    def _on_item_leave(self, index):
        """При уходе с элемента"""
        pass  # Обработано в _on_item_hover
    
    def _on_item_click(self, index):
        """При клике на элемент"""
        self.variable.set(self.values[index])
        self._update_display()
        self._close()
        
        # Вызываем callback если есть
        if hasattr(self, '_command'):
            self._command()
    
    def _on_mousewheel(self, event):
        """Прокрутка в dropdown"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _check_click_outside(self, event):
        """Закрывает dropdown при клике вне его"""
        if not self.dropdown:
            return
        
        # Получаем координаты dropdown
        dx = self.dropdown.winfo_rootx()
        dy = self.dropdown.winfo_rooty()
        dw = self.dropdown.winfo_width()
        dh = self.dropdown.winfo_height()
        
        # Проверяем, попал ли клик в dropdown
        if not (dx <= event.x_root <= dx + dw and dy <= event.y_root <= dy + dh):
            # Проверяем, не попал ли клик в сам виджет
            wx = self.winfo_rootx()
            wy = self.winfo_rooty()
            ww = self.winfo_width()
            wh = self.winfo_height()
            
            if not (wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh):
                self._close()
    
    def bind(self, sequence=None, func=None, add=None):
        """Переопределяем bind для хранения callback"""
        if sequence == "<<ComboboxSelected>>" and func:
            self._command = func
        else:
            super().bind(sequence, func, add)
    
    def set(self, value):
        """Устанавливает значение"""
        self.variable.set(value)
        self._update_display()
    
    def get(self):
        """Получает значение"""
        return self.variable.get()


class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("InWorld TTS")
        self.root.geometry("750x650")
        self.root.resizable(True, True)
        
        # Устанавлием тёмную тему для всего окна
        self.root.configure(bg=COLORS["bg"])
        
        # Для Windows — включаем DWM акценты (эффект стекла)
        try:
            self._enable_dark_mode()
        except:
            pass

        self.current_output_file = None
        self.is_playing = False
        self.is_dragging = False  # Для визуального эффекта при drag

        self._build_ui()
        self._enable_drop()
        self._update_output_filename()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _enable_dark_mode(self):
        """Включает тёмную тему для Windows окна"""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                20,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
        except:
            pass

    def _enable_drop(self):
        """Включает drag-and-drop .txt файлов на всё окно"""
        if not HAS_TKDND:
            print("tkinterdnd2 не установлен, drag-and-drop отключён")
            return
        
        try:
            # Регистрируем drop на главном фрейме (всё окно)
            self.main_frame.drop_target_register(DND_FILES)
            self.main_frame.dnd_bind('<<Drop>>', self._on_drop)
            self.main_frame.dnd_bind('<<DropEnter>>', self._on_drop_enter)
            self.main_frame.dnd_bind('<<DropLeave>>', self._on_drop_leave)
        except Exception as e:
            print(f"Не удалось включить drag-and-drop: {e}")

    def _on_drop_enter(self, event=None):
        """Визуальный эффект при входе файла в зону drop"""
        self.is_dragging = True
        self.main_frame.config(bg=COLORS["dropzone_active"])
        self.drop_frame.config(highlightbackground=COLORS["accent_light"], highlightthickness=3)
        self.drop_label.config(text="📂 Перетащите .txt файл сюда", fg=COLORS["accent_light"])
        return True
    
    def _on_drop_leave(self, event=None):
        """Визуальный эффект при выходе файла из зоны drop"""
        self.is_dragging = False
        self.main_frame.config(bg=COLORS["bg"])
        self.drop_frame.config(highlightbackground=COLORS["border"], highlightthickness=2)
        self.drop_label.config(text="💧 Перетащите .txt файл сюда", fg=COLORS["text_muted"])
        return True

    def _on_drop(self, event=None):
        """Обработка drop файла"""
        self.is_dragging = False
        self.main_frame.config(bg=COLORS["bg"])
        self.drop_frame.config(highlightbackground=COLORS["border"], highlightthickness=2)
        self.drop_label.config(text="💧 Перетащите .txt файл сюда", fg=COLORS["text_muted"])
        
        try:
            # Получаем список файлов из события
            files = self.root.splitlist(event.data)
            for f in files:
                if f.lower().endswith(".txt"):
                    self._load_file(f)
                    return
        except Exception as e:
            print(f"Ошибка при обработке drop: {e}")

    def _build_ui(self):
        # Главный контейнер
        self.main_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Заголовок
        header_frame = tk.Frame(self.main_frame, bg=COLORS["bg_secondary"], height=60)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🎙️ InWorld TTS",
            bg=COLORS["bg_secondary"],
            fg=COLORS["accent_light"],
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Текст в речь",
            bg=COLORS["bg_secondary"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 10)
        )
        subtitle_label.pack(side=tk.LEFT, padx=(0, 20), pady=10)

        # Контент
        content_frame = tk.Frame(self.main_frame, bg=COLORS["bg"])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Зона drag-and-drop (внизу, компактная)
        self.drop_frame = tk.Frame(
            content_frame,
            bg=COLORS["bg_tertiary"],
            highlightbackground=COLORS["border"],
            highlightthickness=2
        )
        self.drop_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.drop_label = tk.Label(
            self.drop_frame,
            text="💧 Перетащите .txt файл сюда",
            bg=COLORS["bg_tertiary"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 9, "italic")
        )
        self.drop_label.pack(pady=8)

        # Выбор голоса
        voice_container = tk.Frame(content_frame, bg=COLORS["bg"])
        voice_container.pack(fill=tk.X, pady=(0, 12))
        
        voice_label = tk.Label(
            voice_container,
            text="Голос:",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 11, "bold")
        )
        voice_label.pack(anchor=tk.W, pady=(0, 5))

        # Кастомный Dropdown
        self.voice_var = tk.StringVar(value=VOICE_DISPLAY[0] if VOICE_DISPLAY else "")
        self.voice_dropdown = DarkDropdown(
            voice_container,
            values=VOICE_DISPLAY,
            variable=self.voice_var,
            font=("Segoe UI", 10)
        )
        self.voice_dropdown.pack(fill=tk.X, pady=(0, 5))
        self.voice_dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_voice_changed())
        
        # Описание голоса
        self.voice_desc_var = tk.StringVar(value="")
        self.voice_desc_label = tk.Label(
            content_frame, 
            textvariable=self.voice_desc_var, 
            fg=COLORS["text_muted"],
            bg=COLORS["bg"],
            font=("Segoe UI", 9, "italic"),
            wraplength=680,
            justify=tk.LEFT
        )
        self.voice_desc_label.pack(anchor=tk.W, pady=(0, 12))
        self._on_voice_changed()

        # Текст
        text_header = tk.Frame(content_frame, bg=COLORS["bg"])
        text_header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(
            text_header,
            text="Текст (без ограничений, авто-разбиение):",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)
        
        self.char_count_var = tk.StringVar(value="0 символов")
        tk.Label(
            text_header, 
            textvariable=self.char_count_var, 
            fg=COLORS["text_muted"],
            bg=COLORS["bg"],
            font=("Segoe UI", 9)
        ).pack(side=tk.RIGHT)

        # Text area с рамкой
        text_border = tk.Frame(content_frame, bg=COLORS["accent"], relief=tk.FLAT)
        text_border.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.text_box = tk.Text(
            text_border, 
            height=10, 
            wrap=tk.WORD,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["bg"],
            font=("Segoe UI", 11),
            relief=tk.FLAT,
            padx=12,
            pady=12,
            highlightthickness=0
        )
        self.text_box.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.text_box.bind("<<Modified>>", self._on_text_change)

        # Кнопки
        btn_container = tk.Frame(content_frame, bg=COLORS["bg"])
        btn_container.pack(fill=tk.X, pady=(0, 10))
        
        # Первая строка кнопок
        btn_row1 = tk.Frame(btn_container, bg=COLORS["bg"])
        btn_row1.pack(fill=tk.X, pady=(0, 8))
        
        self.btn_run = ModernButton(
            btn_row1, 
            text="Сгенерировать", 
            command=self._on_generate,
            icon="⚡",
            bg=COLORS["accent"],
            fg="#ffffff",
            hover_bg=COLORS["accent_hover"],
            font=("Segoe UI", 10, "bold"),
            padding=(20, 10)
        )
        self.btn_run.pack(side=tk.LEFT, padx=(0, 8))
        
        self.btn_play = ModernButton(
            btn_row1,
            text="Прослушать",
            command=self._on_play,
            icon="▶",
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            hover_bg=COLORS["bg_tertiary"],
            font=("Segoe UI", 10),
            padding=(20, 10)
        )
        self.btn_play.pack(side=tk.LEFT, padx=(0, 8))
        
        self.btn_save_as = ModernButton(
            btn_row1,
            text="Сохранить как...",
            command=self._on_save_as,
            icon="💾",
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            hover_bg=COLORS["bg_tertiary"],
            font=("Segoe UI", 10),
            padding=(20, 10)
        )
        self.btn_save_as.pack(side=tk.LEFT)
        
        # Вторая строка кнопок
        btn_row2 = tk.Frame(btn_container, bg=COLORS["bg"])
        btn_row2.pack(fill=tk.X)
        
        self.btn_load_txt = ModernButton(
            btn_row2,
            text="Загрузить .txt",
            command=self._on_load_txt,
            icon="📄",
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            hover_bg=COLORS["bg_tertiary"],
            font=("Segoe UI", 10),
            padding=(20, 10)
        )
        self.btn_load_txt.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_open_folder = ModernButton(
            btn_row2,
            text="Открыть папку",
            command=self._on_open_folder,
            icon="📁",
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            hover_bg=COLORS["bg_tertiary"],
            font=("Segoe UI", 10),
            padding=(20, 10)
        )
        self.btn_open_folder.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_open_batch_folder = ModernButton(
            btn_row2,
            text="Открыть batch",
            command=self._on_open_batch_folder,
            icon="�",
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            hover_bg=COLORS["bg_tertiary"],
            font=("Segoe UI", 10),
            padding=(20, 10)
        )
        self.btn_open_batch_folder.pack(side=tk.LEFT)

        # Статус
        status_container = tk.Frame(content_frame, bg=COLORS["bg"])
        status_container.pack(fill=tk.X, pady=(12, 0))
        
        self.status_var = tk.StringVar(value="✓ Готово")
        self.status_label = tk.Label(
            status_container,
            textvariable=self.status_var,
            fg=COLORS["text_muted"],
            bg=COLORS["bg"],
            font=("Segoe UI", 9),
            anchor=tk.W
        )
        self.status_label.pack(anchor=tk.W)

        # Выходной файл
        self.output_file_var = tk.StringVar(value="")
        tk.Label(
            status_container,
            textvariable=self.output_file_var,
            fg=COLORS["text_muted"],
            bg=COLORS["bg"],
            font=("Segoe UI", 8),
            wraplength=650,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(4, 0))

        # Инициализация
        self._on_voice_changed()


    def _parse_voice_name(self, display_name):
        """Извлекает displayName из 'Name (en)'"""
        if " (" in display_name:
            return display_name.split(" (")[0]
        return display_name

    def _on_voice_changed(self, event=None):
        """Обновляет описание голоса и имя файла"""
        display = self.voice_var.get()
        name = self._parse_voice_name(display)
        voice_info = next((v for v in ALL_VOICES if v["displayName"] == name), None)
        if voice_info:
            desc = voice_info.get("description", "")
            self.voice_desc_var.set(desc if desc else "")
        self._update_output_filename()

    def _update_output_filename(self):
        """Генерирует имя файла на основе текста"""
        if not hasattr(self, 'text_box'):
            return
        text = self.text_box.get("1.0", tk.END).strip()
        if text.endswith("\n"):
            text = text[:-1]
        if not text:
            text = "audio"
        # Берём первые 30 символов, убираем плохие символы
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in text[:30]).strip()
        voice = self.voice_var.get()
        filename = f"{voice}_{safe_name}.wav"
        # Ограничиваем длину
        if len(filename) > 100:
            filename = filename[:100] + ".wav"
        self.current_output_file = os.path.join(OUTPUT_DIR, filename)
        self.output_file_var.set(f"Выход: {self.current_output_file}")

    def _on_text_change(self, event=None):
        text = self.text_box.get("1.0", tk.END)
        if text.endswith("\n"):
            text = text[:-1]
        length = len(text)
        # Убрано ограничение на MAX_CHARS — теперь можно вводить любой текст
        # Batch-обработка сработает автоматически при генерации
        self.char_count_var.set(f"{length} символов")
        self.text_box.edit_modified(False)
        self._update_output_filename()

    def _on_load_txt(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            self._load_file(path)

    def _load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Проверяем размер
            if len(content) > MAX_CHARS:
                chunks = split_text_smart(content, MAX_CHARS)
                result = messagebox.askyesno(
                    "Большой файл",
                    f"Файл содержит {len(content)} символов (лимит: {MAX_CHARS}).\n\n"
                    f"Будет разбит на {len(chunks)} частей и объединён в один файл.\n\n"
                    f"Продолжить?"
                )
                if not result:
                    return
            
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert("1.0", content)
            self._on_text_change()
            self.status_var.set(f"✓ Загружен: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def _on_generate(self):
        text = self.text_box.get("1.0", tk.END).strip()
        if text.endswith("\n"):
            text = text[:-1]
        if not text:
            messagebox.showwarning("Внимание", "Введите текст!")
            return
        
        voice = self.voice_var.get()
        voice_name = self._parse_voice_name(voice)
        voice_id = VOICE_MAP.get(voice_name, voice_name)
        
        # Проверяем размер текста
        is_batch = len(text) > MAX_CHARS
        
        if is_batch:
            # Для больших файлов используем batch_output_dir
            safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in text[:30]).strip()
            filename = f"{voice_name}_{safe_name}_batch.wav"
            if len(filename) > 100:
                filename = filename[:100] + ".wav"
            output = os.path.join(BATCH_OUTPUT_DIR, filename)
            chunks = split_text_smart(text, MAX_CHARS)
            self.status_var.set(f"📝 Текст разбит на {len(chunks)} частей, генерация...")
        else:
            self._update_output_filename()
            output = self.current_output_file

        self.btn_run.config(state=tk.DISABLED, bg=COLORS["text_muted"])
        if not is_batch:
            self.status_var.set("⏳ Генерация...")

        def done(msg, success):
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, bg=COLORS["accent"]))
            self.root.after(0, lambda: self.status_var.set(msg))
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Готово", msg))

        def status(msg):
            self.root.after(0, lambda: self.status_var.set(msg))

        # Запускаем batch или обычную генерацию
        if is_batch:
            threading.Thread(target=run_batch_tts, args=(text, voice_id, output, status, done), daemon=True).start()
        else:
            threading.Thread(target=run_tts, args=(text, voice_id, output, status, done), daemon=True).start()

    def _on_play(self):
        """Воспроизводит сгенерированный файл"""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.btn_play.set_text("▶ Прослушать")
            return

        self._update_output_filename()
        path = self.current_output_file
        if not path or not os.path.exists(path):
            messagebox.showwarning("Внимание", "Сначала сгенерируйте аудио!")
            return

        self.is_playing = True
        self.btn_play.set_text("⏹ Стоп")
        self.status_var.set("🔊 Воспроизведение...")

        def _play_done():
            self.is_playing = False
            self.btn_play.set_text("▶ Прослушать")
            self.status_var.set("✓ Готово")

        def _play_thread():
            try:
                pygame.mixer.init(frequency=48000, size=-16, channels=1)
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    import time
                    time.sleep(0.1)
                pygame.mixer.quit()
                self.root.after(0, _play_done)
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Ошибка воспроизведения: {e}"))
                self.root.after(0, _play_done)

        threading.Thread(target=_play_thread, daemon=True).start()

    def _on_save_as(self):
        self._update_output_filename()
        initial_name = os.path.basename(self.current_output_file)
        path = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")],
            initialfile=initial_name,
            initialdir=OUTPUT_DIR,
        )
        if path:
            self.current_output_file = path
            self.output_file_var.set(f"Выход: {path}")

    def _on_open_folder(self):
        os.startfile(OUTPUT_DIR)

    def _on_open_batch_folder(self):
        os.startfile(BATCH_OUTPUT_DIR)

    def _on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    if HAS_TKDND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = TTSApp(root)
    root.mainloop()

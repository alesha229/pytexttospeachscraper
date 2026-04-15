import requests
import json
import base64
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import ctypes
from ctypes import wintypes
import pygame

# Настройки
URL = "https://inworld.ai/api/create-speech"

# Папка output рядом со скриптом
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

MAX_CHARS = 2000


def create_wav_header(sample_rate, data_size):
    """ Генерирует заголовок WAV файла (44 байта) """
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


# -------- Drag & Drop (pythoncom) --------

def enable_drag_drop(hwnd, on_drop_callback):
    """Включает drag-and-drop .txt файлов на tkinter окно"""
    try:
        import pythoncom

        # Инициализируем COM
        pythoncom.OleInitialize()

        class DropTarget:
            _com_interfaces_ = [pythoncom.IID_IDropTarget]
            _public_methods_ = ['DragEnter', 'DragOver', 'DragLeave', 'Drop']

            def __init__(self, cb):
                self.cb = cb

            def DragEnter(self, dataObj, grfKeyState, pt, pdwEffect):
                self._dataObj = dataObj
                pdwEffect.Value = 1  # DROPEFFECT_COPY
                return 0

            def DragOver(self, grfKeyState, pt, pdwEffect):
                pdwEffect.Value = 1
                return 0

            def DragLeave(self):
                return 0

            def Drop(self, dataObj, grfKeyState, pt, pdwEffect):
                files = self._extract_files(dataObj)
                if files:
                    self.cb(files)
                pdwEffect.Value = 1
                return 0

            def _extract_files(self, dataObj):
                import pythoncom
                from ctypes import windll, create_unicode_buffer

                files = []
                try:
                    # CF_HDROP = 15, TYMED_HGLOBAL = 1
                    fmt = (15, None, 1, -1, pythoncom.TYMED_HGLOBAL)
                    medium = dataObj.GetData(fmt)
                    hdrop = medium.data

                    count = windll.shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                    for i in range(count):
                        buf_len = windll.shell32.DragQueryFileW(hdrop, i, None, 0) + 1
                        buf = create_unicode_buffer(buf_len)
                        windll.shell32.DragQueryFileW(hdrop, i, buf, buf_len)
                        files.append(buf.value)
                    windll.shell32.DragFinish(hdrop)
                except Exception as e:
                    print(f"Drag&drop error: {e}")
                return files

        target = DropTarget(on_drop_callback)
        wrapped = pythoncom.WrapObject(target)
        windll.ole32.RegisterDragDrop(hwnd, wrapped)
        return target
    except Exception as e:
        print(f"Drag&drop не подключён: {e}")
        return None


class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("InWorld TTS")
        self.root.geometry("620x540")
        self.root.resizable(True, True)

        self.current_output_file = None
        self.drop_target = None
        self.is_playing = False

        self._build_ui()
        self._enable_drop()
        self._update_output_filename()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _enable_drop(self):
        """Включает drag-anddrop .txt файлов"""
        def on_drop(files):
            for f in files:
                if f.lower().endswith(".txt"):
                    self._load_file(f)
                    return

        self.drop_target = enable_drag_drop(self.root.winfo_id(), on_drop)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Голос
        ttk.Label(main, text="Голос:").pack(anchor=tk.W)
        self.voice_var = tk.StringVar(value=VOICE_DISPLAY[0] if VOICE_DISPLAY else "")
        self.voice_cb = ttk.Combobox(main, textvariable=self.voice_var, values=VOICE_DISPLAY, state="readonly", width=30)
        self.voice_cb.pack(anchor=tk.W, pady=(0, 5))
        self.voice_cb.bind("<<ComboboxSelected>>", lambda e: self._on_voice_changed())

        # Описание голоса
        self.voice_desc_var = tk.StringVar(value="")
        self.voice_desc_label = ttk.Label(main, textvariable=self.voice_desc_var, foreground="gray", wraplength=550, font=("", 9, "italic"))
        self.voice_desc_label.pack(anchor=tk.W, pady=(0, 10))
        self._on_voice_changed()

        # Текст
        ttk.Label(main, text="Текст (макс. 2000 символов):").pack(anchor=tk.W)
        self.char_count_var = tk.StringVar(value="0 / 2000")
        self.char_label = ttk.Label(main, textvariable=self.char_count_var, foreground="gray")
        self.char_label.pack(anchor=tk.E)

        self.text_box = tk.Text(main, height=10, wrap=tk.WORD)
        self.text_box.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.text_box.bind("<<Modified>>", self._on_text_change)

        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        self.btn_run = ttk.Button(btn_frame, text="Сгенерировать", command=self._on_generate)
        self.btn_run.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_play = ttk.Button(btn_frame, text="▶ Прослушать", command=self._on_play)
        self.btn_play.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_save_as = ttk.Button(btn_frame, text="Сохранить как...", command=self._on_save_as)
        self.btn_save_as.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_load_txt = ttk.Button(btn_frame, text="Загрузить .txt", command=self._on_load_txt)
        self.btn_load_txt.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_open_folder = ttk.Button(btn_frame, text="Открыть папку", command=self._on_open_folder)
        self.btn_open_folder.pack(side=tk.LEFT)

        # Статус
        self.status_var = tk.StringVar(value="Готово")
        self.status_label = ttk.Label(main, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(anchor=tk.W, pady=(10, 0))

        # Выходной файл
        self.output_file_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.output_file_var, foreground="gray", wraplength=550).pack(anchor=tk.W)

        # Инициализация голоса (после создания text_box)
        self._on_voice_changed()

    def _parse_voice_name(self, display_name):
        """Извлекает displayName из 'Name (en)'"""
        if " (" in display_name:
            return display_name.split(" (")[0]
        return display_name

    def _on_voice_changed(self):
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
        if length > MAX_CHARS:
            text = text[:MAX_CHARS]
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert("1.0", text)
            self.text_box.mark_set(tk.INSERT, tk.END)
            length = MAX_CHARS
        self.char_count_var.set(f"{length} / {MAX_CHARS}")
        self.text_box.edit_modified(False)
        self._update_output_filename()

    def _on_load_txt(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            self._load_file(path)

    def _load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()[:MAX_CHARS]
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert("1.0", content)
            self._on_text_change()
            self.status_var.set(f"Загружен: {os.path.basename(path)}")
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

        self._update_output_filename()
        output = self.current_output_file

        self.btn_run.config(state=tk.DISABLED)
        self.status_var.set("Генерация...")

        def done(msg, success):
            self.btn_run.config(state=tk.NORMAL)
            self.status_var.set(msg)
            if success:
                messagebox.showinfo("Готово", msg)

        def status(msg):
            self.status_var.set(msg)

        threading.Thread(target=run_tts, args=(text, voice_id, output, status, done), daemon=True).start()

    def _on_play(self):
        """Воспроизводит сгенерированный файл"""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.btn_play.config(text="▶ Прослушать")
            return

        self._update_output_filename()
        path = self.current_output_file
        if not path or not os.path.exists(path):
            messagebox.showwarning("Внимание", "Сначала сгенерируйте аудио!")
            return

        self.is_playing = True
        self.btn_play.config(text="⏹ Стоп")
        self.status_var.set("Воспроизведение...")

        def _play_done():
            self.is_playing = False
            self.btn_play.config(text="▶ Прослушать")
            self.status_var.set("Готово")

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

    def _on_close(self):
        if self.drop_target:
            self.drop_target.revoke()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TTSApp(root)
    root.mainloop()
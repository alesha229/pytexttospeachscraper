import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

TEMPLATES_DIR = Path(__file__).parent / "templates"
DEFAULT_CONFIG_PATH = TEMPLATES_DIR / "default_montage_config.json"

LOGO_POSITIONS = {
    "top_left": [100, 70],
    "top_right": [1820, 70],
    "bottom_left": [100, 1010],
    "bottom_right": [1820, 1010],
}

TRANSITION_TYPES = [
    "cross_dissolve", "fade_black", "slide_left", "slide_right",
    "zoom_in", "zoom_out", "zoom_dissolve",
    "dolly_push", "dolly_pull", "glitch",
    "whip_pan", "rotate_zoom",
]


class MontageConfig:
    def __init__(self, config_path: str = None):
        self._data = self._load_default()
        if config_path and os.path.exists(config_path):
            self._merge(json.loads(Path(config_path).read_text(encoding="utf-8")))

    def _load_default(self) -> dict:
        if DEFAULT_CONFIG_PATH.exists():
            return json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        return self._builtin_default()

    def _merge(self, override: dict):
        for key, value in override.items():
            if key in self._data and isinstance(self._data[key], dict) and isinstance(value, dict):
                self._data[key].update(value)
            else:
                self._data[key] = value

    @property
    def transitions(self) -> dict:
        return self._data.get("transitions", {})

    @property
    def quote_template(self) -> dict:
        return self._data.get("quote_template", {})

    @property
    def thesis_overlay(self) -> dict:
        return self._data.get("thesis_overlay", {})

    @property
    def real_photo_overlay(self) -> dict:
        return self._data.get("real_photo_overlay", {})

    @property
    def intro(self) -> dict:
        return self._data.get("intro", {})

    @property
    def film_grain(self) -> dict:
        return self._data.get("film_grain", {})

    @property
    def ken_burns(self) -> dict:
        return self._data.get("ken_burns", {})

    @property
    def background_music(self) -> dict:
        return self._data.get("background_music", {})

    @property
    def logo(self) -> dict:
        return self._data.get("logo", {})

    def logo_position_xy(self, width: int = 1920, height: int = 1080) -> list:
        pos_name = self.logo.get("position", "bottom_right")
        if pos_name in LOGO_POSITIONS:
            return LOGO_POSITIONS[pos_name]
        if isinstance(pos_name, list) and len(pos_name) == 2:
            return pos_name
        return [width - 100, height - 70]

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _builtin_default(self) -> dict:
        return {
            "transitions": {"enabled": True, "type": "cross_dissolve", "duration": 0.8},
            "quote_template": {
                "enabled": True,
                "font": "Arial-BoldMT",
                "font_size_quote": 44,
                "font_size_name": 28,
                "layout": "left_photo_right_text",
                "background_opacity": 70,
                "quote_color": [0.95, 0.95, 0.85],
                "name_color": [0.7, 0.7, 0.8],
                "photo_scale": 35,
                "photo_position": "left",
            },
            "thesis_overlay": {
                "enabled": True,
                "fade_in": 0.5,
                "fade_out": 0.5,
                "font": "Arial-Black",
                "font_size": 72,
                "text_color": [1, 1, 1],
                "background_enabled": True,
                "background_color": [0, 0, 0, 180],
            },
            "real_photo_overlay": {
                "enabled": True,
                "search_source": "duckduckgo",
                "scale": 35,
                "position": "center",
                "fade_duration": 0.5,
                "border": True,
                "shadow": True,
            },
            "intro": {
                "enabled": False,
                "duration": 5,
                "style": "dark_minimal",
                "title_font": "Arial-Black",
                "title_size": 80,
                "subtitle_font": "ArialMT",
                "subtitle_size": 36,
            },
            "film_grain": {
                "enabled": False,
                "path": "src/back.mp4",
                "opacity": 15,
                "blend_mode": "overlay",
                "scale": 100,
            },
            "ken_burns": {
                "enabled": True,
                "start_scale": 100,
                "end_scale": 115,
                "pan_x": 0,
                "pan_y": 0,
            },
            "background_music": {"enabled": False, "path": "", "volume": 25},
            "logo": {"enabled": True, "path": "", "position": "bottom_right", "scale": 15, "opacity": 80},
        }

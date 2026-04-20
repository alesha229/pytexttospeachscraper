import json
import os
import wave
import re
import shutil
from typing import Dict, List, Optional
from pathlib import Path

from ..config import TEMPLATES_DIR, AE_OUTPUT_DIR, AE_TEMPLATE


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
        default_path = TEMPLATES_DIR / "default_montage_config.json"
        if default_path.exists():
            return json.loads(default_path.read_text(encoding="utf-8"))
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
            "transitions": {"enabled": True, "type": "cross_dissolve", "duration": 2.0},
            "quote_template": {
                "enabled": True, "font": "Arial-BoldMT", "font_size_quote": 44,
                "font_size_name": 28, "layout": "left_photo_right_text",
                "background_opacity": 70, "quote_color": [0.95, 0.95, 0.85],
                "name_color": [0.7, 0.7, 0.8], "photo_scale": 35, "photo_position": "left",
            },
            "thesis_overlay": {
                "enabled": True, "fade_in": 0.5, "fade_out": 0.5,
                "font": "Arial-Black", "font_size": 72, "text_color": [1, 1, 1],
                "background_enabled": True, "background_color": [0, 0, 0, 180],
            },
            "real_photo_overlay": {
                "enabled": True, "search_source": "duckduckgo", "scale": 35,
                "position": "center", "fade_duration": 0.5, "border": True, "shadow": True,
            },
            "intro": {
                "enabled": False, "duration": 5, "style": "dark_minimal",
                "title_font": "Arial-Black", "title_size": 80,
                "subtitle_font": "ArialMT", "subtitle_size": 36,
            },
            "film_grain": {"enabled": False, "path": "", "opacity": 15, "blend_mode": "overlay", "scale": 100},
            "ken_burns": {"enabled": True, "start_scale": 100, "end_scale": 115, "pan_x": 0, "pan_y": 0},
            "background_music": {"enabled": False, "path": "", "volume": 25},
            "logo": {"enabled": True, "path": "", "position": "bottom_right", "scale": 15, "opacity": 80},
        }


class AEJsonGenerator:
    WIDTH = 1920
    HEIGHT = 1080
    FPS = 24

    def __init__(self, montage_config_path: str = None):
        self.montage_cfg = MontageConfig(montage_config_path)

    def generate(self, scenario: dict, assets_dir: str = None,
                 audio_dir: str = None, output_dir: str = None) -> str:
        is_v3 = "units_manifest" in scenario
        timeline_blocks = scenario.get("timeline", [])

        scene_durs = [self._get_duration(b, audio_dir, i, is_v3) for i, b in enumerate(timeline_blocks)]

        is_news = AE_TEMPLATE == "news"

        intro_offset = 0.0
        ic = self.montage_cfg.intro
        if ic.get("enabled"):
            intro_offset = ic.get("duration", 5)

        FINAL_EDIT_DURATION = 12 if is_news else 0
        total_duration = FINAL_EDIT_DURATION + intro_offset + sum(scene_durs)

        topic = scenario.get("metadata", {}).get("vibe", "project")
        project_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic[:50]).strip()
        save_dir = output_dir or str(AE_OUTPUT_DIR)
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "ae_project.aep")

        units_map = {}
        if is_v3:
            for unit in scenario.get("units_manifest", []):
                units_map[unit.get("id", "")] = unit

        assets_name_to_file = {}
        for asset in scenario.get("assets_manifest", []):
            asset_name = asset.get("name", "")
            asset_type = asset.get("type", "")
            if asset_name and asset_type:
                safe_name = asset_name.replace(" ", "_").lower()
                possible_prefixes = [f"{asset_type}_", "real_", "stock_"]
                found = False
                for prefix in possible_prefixes:
                    if found:
                        break
                    for f in os.listdir(assets_dir):
                        if f.startswith(prefix):
                            filename_no_ext = f.rsplit(".", 1)[0].lower()
                            name_tokens = set(safe_name.split("_"))
                            file_tokens = set(filename_no_ext.split("_"))
                            if name_tokens.issubset(file_tokens):
                                assets_name_to_file[f"{asset_type}:{asset_name}".lower()] = f
                                found = True
                                break

        tl = []
        layer_ids = []

        if is_news:
            tl.append({
                "type": "final_edit",
                "at": 0,
                "duration": FINAL_EDIT_DURATION,
            })

        if ic.get("enabled"):
            tl.append(self._entry_intro(scenario, FINAL_EDIT_DURATION + intro_offset))

        current_time = FINAL_EDIT_DURATION + intro_offset
        for i, block in enumerate(timeline_blocks):
            dur = scene_durs[i]
            lid = f"bg_{i}"
            layer_ids.append(lid)
            tl.append(self._entry_bg(i, lid, current_time, dur, assets_dir))
            audio_entry = self._entry_audio(i, current_time, dur, audio_dir)
            if audio_entry:
                tl.append(audio_entry)
            kb = self._entry_ken_burns(lid, current_time, dur)
            if kb:
                tl.append(kb)
            current_time += dur

        if not is_news:
            grain = self._entry_film_grain(total_duration)
            if grain:
                tl.append(grain)

        tc = self.montage_cfg.transitions
        transitions_enabled = tc.get("enabled") and len(layer_ids) > 1
        overlay_start_margin = 0.5 if transitions_enabled else 0.0
        overlay_end_margin = tc.get("duration", 2.0) + 0.5 if transitions_enabled else 0.0

        current_time = FINAL_EDIT_DURATION + intro_offset
        for i, block in enumerate(timeline_blocks):
            dur = scene_durs[i]
            ov_at = current_time
            ov_dur = dur
            if transitions_enabled:
                if i > 0:
                    ov_at += overlay_start_margin
                    ov_dur -= overlay_start_margin
                if i < len(timeline_blocks) - 1:
                    ov_dur -= overlay_end_margin
            overlays = self._resolve_overlays(block, round(ov_at, 3), round(ov_dur, 3), assets_dir, is_v3, units_map, assets_name_to_file)
            tl.extend(overlays)
            current_time += dur

        if tc.get("enabled") and len(layer_ids) > 1:
            ct = FINAL_EDIT_DURATION + intro_offset
            trans_dur = tc.get("duration", 2.0)
            for i in range(len(scene_durs) - 1):
                ct += scene_durs[i]
                tl.append({
                    "type": "transition", "from": layer_ids[i], "to": layer_ids[i + 1],
                    "style": tc.get("type", "cross_dissolve"), "at": round(ct - trans_dur / 2, 3),
                    "duration": trans_dur,
                })

        music = self._entry_music(total_duration)
        if music:
            tl.append(music)

        logo = self._entry_logo(total_duration)
        if logo:
            tl.append(logo)

        data = {
            "settings": {
                "project_name": project_name, "width": self.WIDTH, "height": self.HEIGHT,
                "fps": self.FPS, "total_duration": round(total_duration, 3),
                "save_path": self._p(save_path),
            },
            "timeline": tl,
        }

        json_path = os.path.join(save_dir, "ae_project.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self._copy_template(save_dir)
        self._print_summary(project_name, len(timeline_blocks), total_duration, json_path, intro_offset)
        return json_path

    def generate_from_project_dir(self, project_dir: str) -> str:
        scenario_path = os.path.join(project_dir, "scenario.json")
        if not os.path.exists(scenario_path):
            raise FileNotFoundError(f"scenario.json not found in {project_dir}")

        with open(scenario_path, "r", encoding="utf-8") as f:
            scenario = json.load(f)

        montage_in_project = os.path.join(project_dir, "montage_config.json")
        if os.path.exists(montage_in_project):
            self.montage_cfg = MontageConfig(montage_in_project)

        json_path = self.generate(
            scenario=scenario,
            assets_dir=os.path.join(project_dir, "assets"),
            audio_dir=os.path.join(project_dir, "audio"),
            output_dir=project_dir,
        )

        self._copy_template(project_dir)
        return json_path

    def _copy_template(self, project_dir: str):
        templates = {
            "news": "ae_template.jsx",
            "scp": "ae_template_scp.jsx",
        }
        for name, filename in templates.items():
            src = TEMPLATES_DIR / filename
            if src.exists():
                dst_name = f"ae_template_{name}.jsx" if name != "news" else "ae_template.jsx"
                dst = os.path.join(project_dir, dst_name)
                shutil.copy2(str(src), dst)
                print(f"JSX ({name}): {dst}")
            else:
                print(f"Warning: template not found: {src}")

        active_src = TEMPLATES_DIR / templates.get(AE_TEMPLATE, "ae_template.jsx")
        if active_src.exists():
            dst = os.path.join(project_dir, "ae_template.jsx")
            shutil.copy2(str(active_src), dst)
            print(f"JSX (active={AE_TEMPLATE}): {dst}")

    def _print_summary(self, name, scenes, duration, json_path, intro_offset):
        print(f"\nAE JSON: {name}")
        print(f"Scenes: {scenes}, Duration: {duration:.1f}s")
        if intro_offset:
            print(f"Intro: +{intro_offset}s")
        cfg = self.montage_cfg
        for n, m in [("Transitions", cfg.transitions), ("Quote", cfg.quote_template),
                      ("Thesis", cfg.thesis_overlay), ("Photo", cfg.real_photo_overlay),
                      ("Intro", cfg.intro), ("Grain", cfg.film_grain),
                      ("Music", cfg.background_music), ("Logo", cfg.logo)]:
            print(f"  {'+' if m.get('enabled') else '-'} {n}")
        print(f"  Template: {AE_TEMPLATE}")
        print(f"Output: {json_path}")

    @staticmethod
    def _p(path: str) -> str:
        if not path:
            return ""
        return os.path.abspath(path).replace("\\", "/")

    def _get_duration(self, block: dict, audio_dir: str = None, idx: int = 0, is_v3: bool = False) -> float:
        if "duration" in block and block["duration"]:
            return block["duration"]
        if is_v3 and "start_time" in block and "end_time" in block:
            return block["end_time"] - block["start_time"]
        if audio_dir and idx >= 0:
            for pat in [f"block_{idx + 1}.wav", f"block_{idx + 1}.mp3", f"audio_{idx + 1}.wav"]:
                fp = os.path.join(audio_dir, pat)
                if os.path.exists(fp):
                    try:
                        with wave.open(fp, "rb") as wf:
                            return wf.getnframes() / wf.getframerate()
                    except Exception:
                        pass
        return 5.0

    def _entry_intro(self, scenario: dict, duration: float) -> dict:
        ic = self.montage_cfg.intro
        return {
            "type": "intro", "at": 0, "duration": duration,
            "title": scenario.get("metadata", {}).get("title", scenario.get("metadata", {}).get("vibe", "Project")),
            "subtitle": scenario.get("metadata", {}).get("subtitle", ""),
            "style": ic.get("style", "dark_minimal"),
            "title_font": ic.get("title_font", "Arial-Black"),
            "title_size": ic.get("title_size", 80),
            "subtitle_font": ic.get("subtitle_font", "ArialMT"),
            "subtitle_size": ic.get("subtitle_size", 36),
        }

    def _entry_bg(self, idx: int, lid: str, at: float, dur: float, assets_dir: str) -> dict:
        patterns = [f"background_{idx + 1}.png", f"background_{idx + 1}.jpg",
                    f"background_{idx + 1}.jpeg", f"background_{idx + 1}.webp"]
        found = self._find_file(assets_dir, patterns)
        if found:
            found = self._fix_extension(found)
            return {"type": "video", "id": lid, "at": round(at, 3), "duration": round(dur, 3),
                    "file": self._p(found), "label": f"BG {idx + 1}"}
        return {"type": "solid", "id": lid, "at": round(at, 3), "duration": round(dur, 3),
                "color": [0.15, 0.15, 0.25], "label": f"BG {idx + 1}"}

    def _entry_audio(self, idx: int, at: float, dur: float, audio_dir: str) -> Optional[dict]:
        patterns = [f"block_{idx + 1}.wav", f"block_{idx + 1}.mp3", f"audio_{idx + 1}.wav"]
        found = self._find_file(audio_dir, patterns)
        if not found:
            return None
        return {"type": "audio", "at": round(at, 3), "duration": round(dur, 3), "file": self._p(found)}

    def _entry_ken_burns(self, lid: str, at: float, dur: float) -> Optional[dict]:
        kb = self.montage_cfg.ken_burns
        if not kb.get("enabled"):
            return None
        return {
            "type": "ken_burns", "target": lid, "at": round(at, 3), "duration": round(dur, 3),
            "start_scale": kb.get("start_scale", 100), "end_scale": kb.get("end_scale", 115),
            "pan_x": kb.get("pan_x", 0), "pan_y": kb.get("pan_y", 0),
        }

    def _entry_film_grain(self, total_dur: float) -> Optional[dict]:
        gc = self.montage_cfg.film_grain
        if not gc.get("enabled"):
            return None
        path = gc.get("path", "")
        if not path:
            fallback = TEMPLATES_DIR / "back.mp4"
            if fallback.exists():
                path = str(fallback)
            else:
                return None
        return {
            "type": "film_grain", "at": 0, "duration": round(total_dur, 3),
            "file": self._p(path), "opacity": gc.get("opacity", gc.get("intensity", 15)),
            "blend_mode": gc.get("blend_mode", "overlay"), "scale": gc.get("scale", 100),
        }

    def _entry_music(self, total_dur: float) -> Optional[dict]:
        mc = self.montage_cfg.background_music
        if not mc.get("enabled"):
            return None
        path = mc.get("path", "")
        if not path:
            return None
        return {"type": "music", "at": 0, "duration": round(total_dur, 3),
                "file": self._p(path), "volume": mc.get("volume", 25)}

    def _entry_logo(self, total_dur: float) -> Optional[dict]:
        lc = self.montage_cfg.logo
        if not lc.get("enabled"):
            return None
        path = lc.get("path", "")
        if not path:
            return None
        xy = LOGO_POSITIONS.get(lc.get("position", "bottom_right"), [self.WIDTH - 100, self.HEIGHT - 70])
        return {
            "type": "logo", "at": 0, "duration": round(total_dur, 3),
            "file": self._p(path), "position_x": xy[0], "position_y": xy[1],
            "scale": lc.get("scale", 15), "opacity": lc.get("opacity", 80),
        }

    def _resolve_overlays(self, block: dict, at: float, dur: float,
                           assets_dir: str, is_v3: bool, units_map: dict,
                           assets_name_to_file: dict = None) -> list:
        overlays = list(block.get("overlays", []))
        if assets_name_to_file is None:
            assets_name_to_file = {}
        if is_v3:
            for unit_ref in block.get("units", []):
                ref_id = unit_ref.get("ref", "")
                role = unit_ref.get("role", "")
                unit = units_map.get(ref_id, {})
                ut = unit.get("type", "")
                if ut == "thesis":
                    overlays.append({"type": "thesis", "content": unit.get("content", ""),
                                     "position": "center", "emphasis": unit.get("emphasis", "medium")})
                elif ut == "quote" and role == "main_quote":
                    overlays.append({"type": "quote", "content": unit.get("content", ""),
                                     "source": unit.get("source", ""), "position": "center"})
                elif ut == "person":
                    asset_key = f"person:{unit.get('name', '')}".lower()
                    full_filename = assets_name_to_file.get(asset_key, "")
                    overlays.append({"type": "person_photo", "name": unit.get("name", ""),
                                     "search_query": unit.get("search_query", ""),
                                     "filename": full_filename})
                elif ut == "object":
                    asset_key = f"object:{unit.get('name', '')}".lower()
                    full_filename = assets_name_to_file.get(asset_key, "")
                    overlays.append({"type": "object_photo", "name": unit.get("name", ""),
                                     "search_query": unit.get("search_query", ""),
                                     "filename": full_filename})

        UNIQUE_TYPES = {"quote", "photo_overlay", "thesis"}
        PRIORITY = {"quote": 0, "photo_overlay": 1, "thesis": 2}
        overlays.sort(key=lambda ov: PRIORITY.get(self._resolve_overlay_type(ov), 99))
        unique_taken = False
        result = []
        idx_in_scene = 0
        for ov in overlays:
            resolved_type = self._resolve_overlay_type(ov)
            if resolved_type in UNIQUE_TYPES and unique_taken:
                continue
            entries = self._build_overlay_entries(ov, at, dur, assets_dir, idx_in_scene)
            if entries:
                if resolved_type in UNIQUE_TYPES:
                    unique_taken = True
                result.extend(entries)
                idx_in_scene += 1
        return result

    @staticmethod
    def _resolve_overlay_type(overlay: dict) -> str:
        o_type = overlay.get("type", "thesis")
        if o_type in ("person_photo", "object_photo"):
            return "photo_overlay"
        return o_type

    def _build_overlay_entries(self, overlay: dict, at: float, dur: float,
                                assets_dir: str, ov_idx: int) -> list:
        o_type = overlay.get("type", "thesis")
        o_text = overlay.get("text") or overlay.get("content", "")
        o_position = overlay.get("position", "center")
        y_map = {"top": 150, "center": self.HEIGHT // 2, "bottom": 950}
        y_pos = y_map.get(o_position, self.HEIGHT // 2)

        if o_type == "thesis" and self.montage_cfg.thesis_overlay.get("enabled"):
            tc = self.montage_cfg.thesis_overlay
            bg_color = tc.get("background_color", [0, 0, 0, 180])
            bg_opacity = round(bg_color[3] / 255.0 * 100) if len(bg_color) == 4 else 70
            return [{"type": "text_overlay", "template": "thesis", "at": round(at, 3),
                     "duration": round(dur, 3), "text": o_text, "style": {
                         "font": tc.get("font", "Arial-Black"), "font_size": tc.get("font_size", 72),
                         "fill_color": tc.get("text_color", [1, 1, 1]), "justification": "CENTER_JUSTIFY",
                         "y_pos": y_pos, "fade_in": tc.get("fade_in", 0.5), "fade_out": tc.get("fade_out", 0.5),
                         "background_enabled": tc.get("background_enabled", True),
                         "background_color": bg_color[:3], "background_opacity": bg_opacity,
                         "background_scale": [50, 10],
                     }}]

        if o_type == "quote" and self.montage_cfg.quote_template.get("enabled"):
            qc = self.montage_cfg.quote_template
            source = overlay.get("source", "")
            search_query = overlay.get("search_query", "")
            photo_path = self._find_person_photo(assets_dir, ov_idx, source, search_query)
            if photo_path:
                photo_path = self._fix_extension(photo_path)
            is_news = AE_TEMPLATE == "news"
            if is_news:
                return [{"type": "quote_template", "at": round(at, 3),
                         "duration": round(dur, 3), "text": o_text, "source": source,
                         "photo_file": self._p(photo_path) if photo_path else None,
                         "frame_number": 3}]
            photo_pos = qc.get("photo_position", "left")
            text_x = int(self.WIDTH * 0.6)
            photo_x = int(self.WIDTH * 0.22)
            if photo_pos == "right":
                text_x = int(self.WIDTH * 0.35)
                photo_x = int(self.WIDTH * 0.75)
            return [{"type": "text_overlay", "template": "quote", "at": round(at, 3),
                     "duration": round(dur, 3), "text": o_text, "source": source,
                     "photo_file": self._p(photo_path) if photo_path else None, "style": {
                         "font": qc.get("font", "Arial-BoldMT"),
                         "font_size_quote": qc.get("font_size_quote", 44),
                         "font_size_name": qc.get("font_size_name", 28),
                         "quote_color": qc.get("quote_color", [0.95, 0.95, 0.85]),
                         "name_color": qc.get("name_color", [0.7, 0.7, 0.8]),
                         "background_opacity": qc.get("background_opacity", 70),
                         "photo_scale": qc.get("photo_scale", 75),
                         "photo_x": photo_x, "photo_y": self.HEIGHT // 2,
                         "text_x": text_x, "text_y": self.HEIGHT // 2 - 30,
                         "name_y": self.HEIGHT // 2 + 60,
                     }}]

        if o_type in ("person_photo", "object_photo") and self.montage_cfg.real_photo_overlay.get("enabled"):
            name = overlay.get("name", o_text)
            search_query = overlay.get("search_query", "")
            full_filename = overlay.get("filename", "")
            if full_filename:
                photo = os.path.join(assets_dir, full_filename) if not os.path.isabs(full_filename) else full_filename
            elif o_type == "person_photo":
                photo = self._find_person_photo(assets_dir, ov_idx, name, search_query)
            else:
                photo = self._find_real_photo(assets_dir, ov_idx, name, search_query)
            if photo:
                photo = self._fix_extension(photo)
            if photo:
                rc = self.montage_cfg.real_photo_overlay
                pos_map = {
                    "center": [self.WIDTH // 2, self.HEIGHT // 2],
                    "top_left": [self.WIDTH // 4, self.HEIGHT // 4],
                    "top_right": [3 * self.WIDTH // 4, self.HEIGHT // 4],
                    "bottom_left": [self.WIDTH // 4, 3 * self.HEIGHT // 4],
                    "bottom_right": [3 * self.WIDTH // 4, 3 * self.HEIGHT // 4],
                }
                xy = pos_map.get(rc.get("position", "center"), pos_map["center"])
                return [{"type": "photo_overlay", "at": round(at, 3), "duration": round(dur, 3),
                         "file": self._p(photo), "style": {
                             "scale": rc.get("scale", 75), "position_x": xy[0], "position_y": xy[1],
                             "fade_duration": rc.get("fade_duration", 0.5), "shadow": rc.get("shadow", True),
                         }}]
            else:
                return [{"type": "text_overlay", "template": "text", "at": round(at, 3),
                         "duration": round(dur, 3), "text": name or o_text, "style": {
                             "font": "Arial-BoldMT", "font_size": 52,
                             "fill_color": [0.7, 0.7, 1], "justification": "CENTER_JUSTIFY", "y_pos": 900,
                         }}]

        if not o_text:
            return []

        if o_type == "quote":
            source = overlay.get("source", "")
            if source:
                o_text = f'"{o_text}" — {source}'

        style_map = {
            "thesis": ("Arial-Black", 80, [1, 1, 1], 400),
            "text_big": ("Arial-Black", 80, [1, 1, 1], 400),
            "quote": ("Arial-ItalicMT", 44, [0.95, 0.95, 0.7], 500),
            "news_item": ("Arial-BoldMT", 40, [0.8, 0.9, 1], 200),
            "nameplate": ("Arial-BoldMT", 52, [0.6, 0.6, 1], 900),
            "text_small": ("ArialMT", 42, [0.9, 0.9, 0.9], 950),
            "subtitle": ("ArialMT", 42, [0.9, 0.9, 0.9], 950),
        }
        font, size, color, default_y = style_map.get(o_type, ("ArialMT", 48, [1, 1, 1], 400))

        if o_type == "news_item":
            headline = overlay.get("headline", o_text)
            src = overlay.get("source", "")
            o_text = f"\U0001f4f0 {headline} ({src})" if src else f"\U0001f4f0 {headline}"

        if o_position == "bottom":
            y_pos = 950
        elif o_position == "top":
            y_pos = 150
        elif o_position == "center":
            y_pos = default_y

        return [{"type": "text_overlay", "template": o_type, "at": round(at, 3),
                 "duration": round(dur, 3), "text": o_text, "style": {
                     "font": font, "font_size": size, "fill_color": color,
                     "justification": "CENTER_JUSTIFY", "y_pos": y_pos,
                 }}]

    @staticmethod
    def _find_file(directory: str, patterns: List[str]) -> Optional[str]:
        if not directory or not os.path.exists(directory):
            return None
        for pattern in patterns:
            filepath = os.path.join(directory, pattern)
            if os.path.exists(filepath):
                return filepath
        return None

    @staticmethod
    def _detect_image_format(filepath: str) -> str:
        if not filepath or not os.path.exists(filepath):
            return "unknown"
        try:
            with open(filepath, "rb") as f:
                header = f.read(12)
            if header[:8] == b"\x89PNG\r\n\x1a\n":
                return "png"
            if header[:2] == b"\xff\xd8":
                return "jpeg"
            if header[:2] == b"BM":
                return "bmp"
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                return "webp"
        except Exception:
            pass
        return "unknown"

    def _fix_extension(self, filepath: str) -> str:
        if not filepath or not os.path.exists(filepath):
            return filepath
        fmt = self._detect_image_format(filepath)
        if fmt == "unknown":
            return filepath
        ext_map = {"png": ".png", "jpeg": ".jpg", "bmp": ".bmp", "webp": ".webp"}
        correct_ext = ext_map.get(fmt)
        if not correct_ext:
            return filepath
        current_ext = os.path.splitext(filepath)[1].lower()
        if current_ext == correct_ext:
            return filepath
        if fmt == "webp":
            new_path = filepath.rsplit(".", 1)[0] + "_webp.png"
            try:
                from PIL import Image
                Image.open(filepath).save(new_path, "PNG")
                return new_path
            except Exception:
                return filepath
        new_path = filepath.rsplit(".", 1)[0] + correct_ext
        try:
            os.rename(filepath, new_path)
            return new_path
        except Exception:
            return filepath

    def _build_asset_name_map(self, assets_dir: str) -> dict:
        result = {}
        if not assets_dir or not os.path.exists(assets_dir):
            return result
        for f in os.listdir(assets_dir):
            for prefix in ("real_", "stock_", "person_", "object_", "location_"):
                if f.startswith(prefix):
                    name_part = f[len(prefix):].rsplit(".", 1)[0].replace("_", " ").lower()
                    path = os.path.join(assets_dir, f)
                    if name_part not in result:
                        result[name_part] = path
                    for token in name_part.split():
                        if len(token) > 2 and token not in result:
                            result[token] = path
                    break
        return result

    def _fuzzy_find_asset(self, assets_dir: str, name: str, search_query: str = "") -> Optional[str]:
        if not name and not search_query:
            return None
        anm = self._build_asset_name_map(assets_dir)
        search_terms = [t.lower().strip() for t in [name, search_query] if t]
        best = None
        best_score = 0
        for key, path in anm.items():
            for term in search_terms:
                tw = set(term.split())
                kw = set(key.split())
                if key == term:
                    return path
                overlap = len(tw & kw)
                if overlap > best_score:
                    best_score = overlap
                    best = path
        return best

    def _find_real_photo(self, assets_dir: str, idx: int, name: str = "", search_query: str = "") -> Optional[str]:
        if not assets_dir or not os.path.exists(assets_dir):
            return None
        candidates = []
        if name:
            safe = name.replace(" ", "_")
            candidates.extend([f"real_{safe}.jpg", f"real_{safe}.png",
                               f"stock_{safe}.jpg", f"stock_{safe}.png",
                               f"object_{safe}.jpg", f"object_{safe}.png",
                               f"location_{safe}.jpg", f"location_{safe}.png"])
        if search_query:
            safe_q = re.sub(r'[^a-zA-Z0-9_\s]', '', search_query).replace(' ', '_')
            if safe_q and safe_q != (name.replace(" ", "_") if name else ""):
                candidates.extend([f"real_{safe_q}.jpg", f"real_{safe_q}.png",
                                   f"stock_{safe_q}.jpg", f"stock_{safe_q}.png"])
        candidates.extend([f"bg_real_person_{idx + 1}.jpg", f"bg_real_person_{idx + 1}.png",
                           f"bg_real_{idx + 1}.jpg", f"bg_real_{idx + 1}.png", f"bg_stock_{idx + 1}.jpg"])
        found = self._find_file(assets_dir, candidates)
        if found:
            return found
        return self._fuzzy_find_asset(assets_dir, name, search_query)

    def _find_person_photo(self, assets_dir: str, idx: int, person_name: str = "",
                            search_query: str = "") -> Optional[str]:
        if not assets_dir or not os.path.exists(assets_dir):
            return None
        
        if person_name:
            safe_name = person_name.replace(" ", "_")
            for f in os.listdir(assets_dir):
                if f.startswith("person_") and safe_name.lower() in f.lower():
                    return os.path.join(assets_dir, f)
        
        if search_query:
            safe_q = re.sub(r'[^a-zA-Z0-9_\s]', '', search_query).replace(' ', '_')
            for f in os.listdir(assets_dir):
                if f.startswith("person_") and safe_q.lower() in f.lower():
                    return os.path.join(assets_dir, f)
        
        return self._fuzzy_find_asset(assets_dir, person_name, search_query)

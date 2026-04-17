import sys
import os as _os

sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
import os
import json
import wave
import re
from typing import Dict, List, Optional
from pathlib import Path

from src.video.ae_montage_config import MontageConfig, LOGO_POSITIONS


class AEJsonGenerator:
    WIDTH = 1920
    HEIGHT = 1080
    FPS = 24

    def __init__(self, montage_config_path: str = None):
        self.montage_cfg = MontageConfig(montage_config_path)

    def generate(
        self,
        scenario: dict,
        assets_dir: str = None,
        audio_dir: str = None,
        output_dir: str = None,
    ) -> str:
        is_v3 = "units_manifest" in scenario
        timeline_blocks = scenario.get("timeline", [])

        scene_durs = [self._get_duration(b, audio_dir, i, is_v3) for i, b in enumerate(timeline_blocks)]

        intro_offset = 0.0
        ic = self.montage_cfg.intro
        if ic.get("enabled"):
            intro_offset = ic.get("duration", 5)

        total_duration = intro_offset + sum(scene_durs)

        topic = scenario.get("metadata", {}).get("vibe", "project")
        project_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic[:50]).strip()
        save_dir = output_dir or "./ae_output"
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "ae_project.aep")

        units_map = {}
        if is_v3:
            for unit in scenario.get("units_manifest", []):
                units_map[unit.get("id", "")] = unit

        tl = []
        layer_ids = []

        if ic.get("enabled"):
            tl.append(self._entry_intro(scenario, intro_offset))

        current_time = intro_offset
        for i, block in enumerate(timeline_blocks):
            dur = scene_durs[i]
            lid = f"bg_{i}"
            layer_ids.append(lid)

            bg_entry = self._entry_bg(i, lid, current_time, dur, assets_dir)
            tl.append(bg_entry)

            audio_entry = self._entry_audio(i, current_time, dur, audio_dir)
            if audio_entry:
                tl.append(audio_entry)

            kb = self._entry_ken_burns(lid, current_time, dur)
            if kb:
                tl.append(kb)

            current_time += dur

        grain = self._entry_film_grain(total_duration)
        if grain:
            tl.append(grain)

        current_time = intro_offset
        for i, block in enumerate(timeline_blocks):
            dur = scene_durs[i]
            overlays = self._resolve_overlays(block, current_time, dur, assets_dir, is_v3, units_map)
            tl.extend(overlays)
            current_time += dur

        tc = self.montage_cfg.transitions
        if tc.get("enabled") and len(layer_ids) > 1:
            ct = intro_offset
            for i in range(len(scene_durs) - 1):
                ct += scene_durs[i]
                tl.append({
                    "type": "transition",
                    "from": layer_ids[i],
                    "to": layer_ids[i + 1],
                    "style": tc.get("type", "cross_dissolve"),
                    "at": round(ct, 3),
                    "duration": tc.get("duration", 0.8),
                })

        music = self._entry_music(total_duration)
        if music:
            tl.append(music)

        logo = self._entry_logo(total_duration)
        if logo:
            tl.append(logo)

        data = {
            "settings": {
                "project_name": project_name,
                "width": self.WIDTH,
                "height": self.HEIGHT,
                "fps": self.FPS,
                "total_duration": round(total_duration, 3),
                "save_path": self._p(save_path),
            },
            "timeline": tl,
        }

        json_path = os.path.join(save_dir, "ae_project.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

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
        import shutil
        template_src = Path(__file__).parent / "templates" / "ae_template.jsx"
        if template_src.exists():
            dst = os.path.join(project_dir, "ae_template.jsx")
            shutil.copy2(str(template_src), dst)
            print(f"JSX: {dst}")

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
            for pat in [f"block_{idx+1}.wav", f"block_{idx+1}.mp3", f"audio_{idx+1}.wav"]:
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
            "type": "intro",
            "at": 0,
            "duration": duration,
            "title": scenario.get("metadata", {}).get("title", scenario.get("metadata", {}).get("vibe", "Project")),
            "subtitle": scenario.get("metadata", {}).get("subtitle", ""),
            "style": ic.get("style", "dark_minimal"),
            "title_font": ic.get("title_font", "Arial-Black"),
            "title_size": ic.get("title_size", 80),
            "subtitle_font": ic.get("subtitle_font", "ArialMT"),
            "subtitle_size": ic.get("subtitle_size", 36),
        }

    def _entry_bg(self, idx: int, lid: str, at: float, dur: float, assets_dir: str) -> dict:
        patterns = [f"background_{idx+1}.png", f"background_{idx+1}.jpg", f"background_{idx+1}.jpeg",
                    f"background_{idx+1}.webp"]
        found = self._find_file(assets_dir, patterns)
        if found:
            found = self._fix_extension(found)
            return {"type": "video", "id": lid, "at": round(at, 3), "duration": round(dur, 3),
                    "file": self._p(found), "label": f"BG {idx+1}"}
        return {"type": "solid", "id": lid, "at": round(at, 3), "duration": round(dur, 3),
                "color": [0.15, 0.15, 0.25], "label": f"BG {idx+1}"}

    def _entry_audio(self, idx: int, at: float, dur: float, audio_dir: str) -> Optional[dict]:
        patterns = [f"block_{idx+1}.wav", f"block_{idx+1}.mp3", f"audio_{idx+1}.wav"]
        found = self._find_file(audio_dir, patterns)
        if not found:
            return None
        return {"type": "audio", "at": round(at, 3), "duration": round(dur, 3), "file": self._p(found)}

    def _entry_ken_burns(self, lid: str, at: float, dur: float) -> Optional[dict]:
        kb = self.montage_cfg.ken_burns
        if not kb.get("enabled"):
            return None
        return {
            "type": "ken_burns",
            "target": lid,
            "at": round(at, 3),
            "duration": round(dur, 3),
            "start_scale": kb.get("start_scale", 100),
            "end_scale": kb.get("end_scale", 115),
            "pan_x": kb.get("pan_x", 0),
            "pan_y": kb.get("pan_y", 0),
        }

    def _entry_film_grain(self, total_dur: float) -> Optional[dict]:
        gc = self.montage_cfg.film_grain
        if not gc.get("enabled"):
            return None
        path = gc.get("path", "")
        if not path:
            fallback = Path(__file__).parent / "templates" / "back.mp4"
            if fallback.exists():
                path = str(fallback)
            else:
                return None
        return {
            "type": "film_grain",
            "at": 0,
            "duration": round(total_dur, 3),
            "file": self._p(path),
            "opacity": gc.get("opacity", gc.get("intensity", 15)),
            "blend_mode": gc.get("blend_mode", "overlay"),
            "scale": gc.get("scale", 100),
        }

    def _entry_music(self, total_dur: float) -> Optional[dict]:
        mc = self.montage_cfg.background_music
        if not mc.get("enabled"):
            return None
        path = mc.get("path", "")
        if not path:
            return None
        return {
            "type": "music",
            "at": 0,
            "duration": round(total_dur, 3),
            "file": self._p(path),
            "volume": mc.get("volume", 25),
        }

    def _entry_logo(self, total_dur: float) -> Optional[dict]:
        lc = self.montage_cfg.logo
        if not lc.get("enabled"):
            return None
        path = lc.get("path", "")
        if not path:
            return None
        xy = LOGO_POSITIONS.get(lc.get("position", "bottom_right"), [self.WIDTH - 100, self.HEIGHT - 70])
        return {
            "type": "logo",
            "at": 0,
            "duration": round(total_dur, 3),
            "file": self._p(path),
            "position_x": xy[0],
            "position_y": xy[1],
            "scale": lc.get("scale", 15),
            "opacity": lc.get("opacity", 80),
        }

    def _resolve_overlays(self, block: dict, at: float, dur: float,
                          assets_dir: str, is_v3: bool, units_map: dict) -> list:
        overlays = list(block.get("overlays", []))

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
                    overlays.append({"type": "person_photo", "name": unit.get("name", ""),
                                     "search_query": unit.get("search_query", "")})
                elif ut == "object":
                    overlays.append({"type": "object_photo", "name": unit.get("name", ""),
                                     "search_query": unit.get("search_query", "")})

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
            return [{
                "type": "text_overlay",
                "template": "thesis",
                "at": round(at, 3),
                "duration": round(dur, 3),
                "text": o_text,
                "style": {
                    "font": tc.get("font", "Arial-Black"),
                    "font_size": tc.get("font_size", 72),
                    "fill_color": tc.get("text_color", [1, 1, 1]),
                    "justification": "CENTER_JUSTIFY",
                    "y_pos": y_pos,
                    "fade_in": tc.get("fade_in", 0.5),
                    "fade_out": tc.get("fade_out", 0.5),
                    "background_enabled": tc.get("background_enabled", True),
                    "background_color": bg_color[:3],
                    "background_opacity": bg_opacity,
                    "background_scale": [50, 10],
                },
            }]

        if o_type == "quote" and self.montage_cfg.quote_template.get("enabled"):
            qc = self.montage_cfg.quote_template
            source = overlay.get("source", "")
            search_query = overlay.get("search_query", "")
            photo_path = self._find_person_photo(assets_dir, ov_idx, source, search_query)
            if photo_path:
                photo_path = self._fix_extension(photo_path)

            photo_pos = qc.get("photo_position", "left")
            text_x = int(self.WIDTH * 0.6)
            photo_x = int(self.WIDTH * 0.22)
            if photo_pos == "right":
                text_x = int(self.WIDTH * 0.35)
                photo_x = int(self.WIDTH * 0.75)

            return [{
                "type": "text_overlay",
                "template": "quote",
                "at": round(at, 3),
                "duration": round(dur, 3),
                "text": o_text,
                "source": source,
                "photo_file": self._p(photo_path) if photo_path else None,
                "style": {
                    "font": qc.get("font", "Arial-BoldMT"),
                    "font_size_quote": qc.get("font_size_quote", 44),
                    "font_size_name": qc.get("font_size_name", 28),
                    "quote_color": qc.get("quote_color", [0.95, 0.95, 0.85]),
                    "name_color": qc.get("name_color", [0.7, 0.7, 0.8]),
                    "background_opacity": qc.get("background_opacity", 70),
                    "photo_scale": qc.get("photo_scale", 35),
                    "photo_x": photo_x,
                    "photo_y": self.HEIGHT // 2,
                    "text_x": text_x,
                    "text_y": self.HEIGHT // 2 - 30,
                    "name_y": self.HEIGHT // 2 + 60,
                },
            }]

        if o_type in ("person_photo", "object_photo") and self.montage_cfg.real_photo_overlay.get("enabled"):
            name = overlay.get("name", o_text)
            search_query = overlay.get("search_query", "")
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
                return [{
                    "type": "photo_overlay",
                    "at": round(at, 3),
                    "duration": round(dur, 3),
                    "file": self._p(photo),
                    "style": {
                        "scale": rc.get("scale", 35),
                        "position_x": xy[0],
                        "position_y": xy[1],
                        "fade_duration": rc.get("fade_duration", 0.5),
                        "shadow": rc.get("shadow", True),
                    },
                }]
            else:
                return [{
                    "type": "text_overlay",
                    "template": "text",
                    "at": round(at, 3),
                    "duration": round(dur, 3),
                    "text": name or o_text,
                    "style": {
                        "font": "Arial-BoldMT",
                        "font_size": 52,
                        "fill_color": [0.7, 0.7, 1],
                        "justification": "CENTER_JUSTIFY",
                        "y_pos": 900,
                    },
                }]

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
            o_text = f"\ud83d\udcf0 {headline} ({src})" if src else f"\ud83d\udcf0 {headline}"

        if o_position == "bottom":
            y_pos = 950
        elif o_position == "top":
            y_pos = 150
        elif o_position == "center":
            y_pos = default_y

        return [{
            "type": "text_overlay",
            "template": o_type,
            "at": round(at, 3),
            "duration": round(dur, 3),
            "text": o_text,
            "style": {
                "font": font,
                "font_size": size,
                "fill_color": color,
                "justification": "CENTER_JUSTIFY",
                "y_pos": y_pos,
            },
        }]

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
            candidates.extend([
                f"real_{safe}.jpg", f"real_{safe}.png",
                f"stock_{safe}.jpg", f"stock_{safe}.png",
                f"object_{safe}.jpg", f"object_{safe}.png",
                f"location_{safe}.jpg", f"location_{safe}.png",
            ])
        if search_query:
            safe_q = re.sub(r'[^a-zA-Z0-9_\s]', '', search_query).replace(' ', '_')
            if safe_q and safe_q != (name.replace(" ", "_") if name else ""):
                candidates.extend([
                    f"real_{safe_q}.jpg", f"real_{safe_q}.png",
                    f"stock_{safe_q}.jpg", f"stock_{safe_q}.png",
                ])
        candidates.extend([
            f"bg_real_person_{idx+1}.jpg", f"bg_real_person_{idx+1}.png",
            f"bg_real_{idx+1}.jpg", f"bg_real_{idx+1}.png",
            f"bg_stock_{idx+1}.jpg",
        ])
        found = self._find_file(assets_dir, candidates)
        if found:
            return found
        return self._fuzzy_find_asset(assets_dir, name, search_query)

    def _find_person_photo(self, assets_dir: str, idx: int, person_name: str = "",
                           search_query: str = "") -> Optional[str]:
        if not assets_dir or not os.path.exists(assets_dir):
            return None
        candidates = []
        if person_name:
            safe = person_name.replace(" ", "_")
            candidates.extend([
                f"real_{safe}.jpg", f"real_{safe}.png",
                f"person_{safe}.jpg", f"person_{safe}.png",
                f"person_{safe}_placeholder.png",
            ])
        if search_query:
            safe_q = re.sub(r'[^a-zA-Z0-9_\s]', '', search_query).replace(' ', '_')
            if safe_q and safe_q != (person_name.replace(" ", "_") if person_name else ""):
                candidates.extend([
                    f"real_{safe_q}.jpg", f"real_{safe_q}.png",
                ])
        candidates.extend([
            f"bg_real_person_{idx+1}.jpg", f"bg_real_person_{idx+1}.png",
        ])
        found = self._find_file(assets_dir, candidates)
        if found:
            return found
        return self._fuzzy_find_asset(assets_dir, person_name, search_query)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="AE JSON Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python ae_json_generator.py ./video_output_v2/MyTopic_123456

Auto-detected from project dir:
  scenario.json     (required)
  montage_config.json  (optional, uses defaults if missing)
  assets/           (background images)
  audio/            (voiceover audio)

Output (in project dir):
  ae_project.json   (data for AE engine)
  ae_template.jsx   (AE engine script)
        """,
    )
    parser.add_argument("project_dir", help="Project dir with scenario.json + assets/ + audio/")

    args = parser.parse_args()

    gen = AEJsonGenerator()
    gen.generate_from_project_dir(args.project_dir)


if __name__ == "__main__":
    main()

"""
After Effects Project Generator
================================
Генерирует ExtendScript (.jsx) для After Effects из готового сценария и ассетов.
Можно тестировать на pre-generated ассетах без перегенерации.

Использование:
    # Полный режим (сценарий + ассеты)
    python ae_project_generator.py --scenario scenario.json --assets-dir ./assets --audio-dir ./audio

    # Preview режим (только структура, без файлов)
    python ae_project_generator.py --scenario scenario.json --preview

    # Режим с готовым проектом (все ассеты уже есть)
    python ae_project_generator.py --project-dir ./video_output_v2/Topic_123456

Вход:
    - scenario.json: Сценарий V2
    - assets/: Изображения (background_N.png)
    - audio/: Аудио (block_N.wav)
    - overlays/: Оверлеи (block_N_overlays.png)

Выход:
    - .jsx скрипт → открыть в AE: File → Scripts → Run Script File
"""

import os
import json
import time
import wave
from typing import Dict, List, Optional
from pathlib import Path


class AEProjectGenerator:
    """Генератор After Effects проектов через ExtendScript (.jsx)"""
    
    WIDTH = 1920
    HEIGHT = 1080
    FPS = 24
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or "./ae_output"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_from_scenario(
        self,
        scenario: dict,
        assets_dir: str = None,
        audio_dir: str = None,
        preview: bool = False
    ) -> str:
        """
        Генерирует .jsx скрипт из сценария (поддержка V2 и V3 форматов)
        """
        # Определяем формат сценария
        is_v3 = "units_manifest" in scenario
        
        timeline = scenario.get("timeline", [])
        
        if is_v3:
            # V3 формат: units_manifest + timeline с ссылками
            total_duration = sum(self._get_block_duration_v3(block, audio_dir, i) for i, block in enumerate(timeline))
        else:
            # V2 формат: обычный
            total_duration = sum(self._get_block_duration(block, audio_dir, i) for i, block in enumerate(timeline))
        
        topic = scenario.get("metadata", {}).get("vibe", "project")
        project_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic[:50]).strip()
        timestamp = int(time.time())
        jsx_path = os.path.join(self.output_dir, f"{project_name}_{timestamp}.jsx")
        
        print(f"\n🎬 Генерация AE проекта: {project_name}")
        print(f"📊 Сцен: {len(timeline)}, Длительность: {total_duration:.1f} сек")
        print(f"📂 Выход: {jsx_path}")
        
        if preview:
            jsx = self._build_preview_jsx(scenario, audio_dir, is_v3)
        else:
            jsx = self._build_full_jsx(scenario, assets_dir, audio_dir, total_duration, is_v3)
        
        with open(jsx_path, "w", encoding="utf-8") as f:
            f.write(jsx)
        
        print(f"✅ AE скрипт создан: {jsx_path}")
        if not preview:
            print(f"📌 Откройте AE → File → Scripts → Run Script File → выберите {jsx_path}")
        else:
            print(f"📌 Preview режим: откройте AE → File → Scripts → Run Script File → выберите {jsx_path}")
        
        return jsx_path
    
    def generate_from_project_dir(self, project_dir: str, preview: bool = False) -> str:
        """
        Генерирует .jsx из готовой папки проекта video_output_v2/
        .jsx файл создается в той же папке
        
        Args:
            project_dir: Папка проекта (с scenario.json, assets/, audio/, overlays/)
            preview: Если True - создает проект без внешних файлов
            
        Returns:
            Путь к .jsx файлу
        """
        scenario_path = os.path.join(project_dir, "scenario.json")
        if not os.path.exists(scenario_path):
            raise FileNotFoundError(f"scenario.json не найден в {project_dir}")
        
        with open(scenario_path, "r", encoding="utf-8") as f:
            scenario = json.load(f)
        
        assets_dir = os.path.join(project_dir, "assets")
        audio_dir = os.path.join(project_dir, "audio")
        
        # Генерируем jsx прямо в папку проекта
        self.output_dir = project_dir
        
        return self.generate_from_scenario(
            scenario=scenario,
            assets_dir=assets_dir,
            audio_dir=audio_dir,
            preview=preview
        )
    
    def _get_block_duration(self, block: dict, audio_dir: str = None, block_index: int = 0) -> float:
        """Определяет длительность блока по реальному аудиофайлу (V2 формат)"""
        if "duration" in block and block["duration"]:
            return block["duration"]
        
        if audio_dir and block_index >= 0:
            audio_patterns = [f"block_{block_index+1}.wav", f"block_{block_index+1}.mp3", f"audio_{block_index+1}.wav"]
            for pattern in audio_patterns:
                audio_path = os.path.join(audio_dir, pattern)
                if os.path.exists(audio_path):
                    try:
                        with wave.open(audio_path, 'rb') as wf:
                            return wf.getnframes() / wf.getframerate()
                    except:
                        pass
        
        return 5.0
    
    def _get_block_duration_v3(self, block: dict, audio_dir: str = None, block_index: int = 0) -> float:
        """Определяет длительность блока для V3 формата"""
        # V3 использует duration или start_time/end_time
        if "duration" in block:
            return block["duration"]
        if "start_time" in block and "end_time" in block:
            return block["end_time"] - block["start_time"]
        
        # Fallback к аудиофайлу
        if audio_dir and block_index >= 0:
            audio_patterns = [f"block_{block_index+1}.wav", f"block_{block_index+1}.mp3"]
            for pattern in audio_patterns:
                audio_path = os.path.join(audio_dir, pattern)
                if os.path.exists(audio_path):
                    try:
                        with wave.open(audio_path, 'rb') as wf:
                            return wf.getnframes() / wf.getframerate()
                    except:
                        pass
        
        return 5.0
    
    def _escape_jsx_string(self, s: str) -> str:
        """Экранирует строку для JSX"""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    
    def _to_jsx_path(self, path: str) -> str:
        """Конвертирует путь в формат JSX (Windows)"""
        if not path:
            return ""
        # Конвертируем в абсолютный путь
        abs_path = os.path.abspath(path)
        # Заменяем обратные слеши на двойные для JSX
        return abs_path.replace("\\", "\\\\")
    
    def _find_file(self, directory: str, patterns: List[str]) -> Optional[str]:
        """Ищет файл по нескольким паттернам"""
        if not directory or not os.path.exists(directory):
            return None
        for pattern in patterns:
            filepath = os.path.join(directory, pattern)
            if os.path.exists(filepath):
                return filepath
        return None
    
    def _detect_image_format(self, filepath: str) -> str:
        """Определяет реальный формат изображения по сигнатуре"""
        if not filepath or not os.path.exists(filepath):
            return "unknown"
        try:
            with open(filepath, "rb") as f:
                header = f.read(8)
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                return "png"
            elif header[:2] == b'\xff\xd8':
                return "jpeg"
            elif header[:2] == b'BM':
                return "bmp"
            elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                return "webp"
        except:
            pass
        return "unknown"
    
    def _build_full_jsx(
        self,
        scenario: dict,
        assets_dir: str,
        audio_dir: str,
        total_duration: float,
        is_v3: bool = False
    ) -> str:
        """Строит полный JSX скрипт с файлами"""
        timeline = scenario.get("timeline", [])
        
        # Для V3 загружаем units_manifest
        units_map = {}
        if is_v3:
            for unit in scenario.get("units_manifest", []):
                units_map[unit.get("id", "")] = unit
        
        # Рассчитываем длительности сцен по аудиофайлам
        scene_durations = []
        for i, block in enumerate(timeline):
            if is_v3:
                duration = self._get_block_duration_v3(block, audio_dir, i)
            else:
                duration = self._get_block_duration(block, audio_dir, i)
            scene_durations.append(duration)
        
        jsx = f"""// After Effects ExtendScript
// Project: {self._escape_jsx_string(scenario.get("metadata", {}).get("vibe", "Project"))}
// Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
// Scenes: {len(timeline)}
// Duration: {total_duration:.1f}s

#target aftereffects

(function() {{
    // Создаем проект если нет
    if (!app.project) {{
        app.newProject();
    }}
    
    var project = app.project;
    var W = {self.WIDTH};
    var H = {self.HEIGHT};
    var FPS = {self.FPS};
    var DUR = {total_duration};
    
    // Главная композиция
    var mainComp = project.items.addComp(
        "Main Composition",
        W, H, 1.0, DUR, FPS
    );
    mainComp.openInViewer();
    
    // Утилиты
    function importFile(path) {{
        var io = new ImportOptions();
        io.file = new File(path);
        return project.importFile(io);
    }}
    
    function addFootageLayer(comp, footage, start, dur, name) {{
        var layer = comp.layers.add(footage);
        layer.name = name;
        layer.startTime = start;
        layer.outPoint = start + dur;
        return layer;
    }}
    
    function addText(comp, text, start, dur, name, size, x, y, color) {{
        var tl = comp.layers.addText(text);
        tl.name = name;
        tl.startTime = start;
        tl.outPoint = start + dur;
        
        var tp = tl.property("Source Text");
        var td = tp.value;
        td.fontSize = size;
        td.font = "Arial-BoldMT";
        td.justification = ParagraphJustification.CENTER_JUSTIFY;
        td.fillColor = color || [1, 1, 1];
        tp.setValue(td);
        
        tl.property("Position").setValue([x, y]);
        return tl;
    }}
    
"""
        
        current_time = 0
        for i, block in enumerate(timeline):
            duration = scene_durations[i]
            voiceover = block.get("voiceover", "")
            
            # V2 формат: overlays массив
            overlays = block.get("overlays", [])
            
            # V3 формат: units ссылки
            if is_v3:
                units_refs = block.get("units", [])
                for unit_ref in units_refs:
                    ref_id = unit_ref.get("ref", "")
                    role = unit_ref.get("role", "")
                    unit = units_map.get(ref_id, {})
                    
                    if unit.get("type") == "thesis":
                        overlays.append({
                            "type": "thesis",
                            "content": unit.get("content", ""),
                            "position": "center",
                            "emphasis": unit.get("emphasis", "medium")
                        })
                    elif unit.get("type") == "quote" and role == "main_quote":
                        overlays.append({
                            "type": "quote",
                            "content": unit.get("content", ""),
                            "source": unit.get("source", ""),
                            "position": "center"
                        })
            
            jsx += f"    // === Scene {i+1} (t={current_time:.1f}s - {current_time+duration:.1f}s) ===\n"
            
            # Background
            bg_patterns = [f"background_{i+1}.png", f"background_{i+1}.jpg", f"background_{i+1}.jpeg"]
            bg_file = self._find_file(assets_dir, bg_patterns)
            
            if bg_file:
                # Определяем реальный формат и переименовываем если нужно
                real_format = self._detect_image_format(bg_file)
                if real_format == "jpeg" and bg_file.lower().endswith(".png"):
                    # Переименовываем в .jpg
                    new_path = bg_file[:-4] + ".jpg"
                    try:
                        os.rename(bg_file, new_path)
                        bg_file = new_path
                    except:
                        pass  # Если не удалось переименовать, используем как есть
                
                jsx += f"""    try {{
        var bg{i} = importFile("{self._to_jsx_path(bg_file)}");
        addFootageLayer(mainComp, bg{i}, {current_time}, {duration}, "BG {i+1}");
    }} catch(e) {{ $.writeln("BG {i+1}: " + e); }}
"""
            else:
                # Solid fallback
                jsx += f"""    var solid{i} = project.items.addSolid([0.15, 0.15, 0.25], "BG {i+1} (solid)", W, H, 1.0);
    addFootageLayer(mainComp, solid{i}, {current_time}, {duration}, "BG {i+1}");
"""
            
            # Текстовые оверлеи из сценария (юниты)
            for j, overlay in enumerate(overlays):
                # Поддержка форматов: старый (type/text) и новый (type/content)
                o_type = overlay.get("type", "thesis")
                o_text = overlay.get("text") or overlay.get("content", "")
                o_position = overlay.get("position", "center")
                
                if not o_text:
                    continue
                
                # Маппинг типов в AE стили
                if o_type == "thesis":
                    # Короткий тезис - крупно по центру
                    size, y_pos, color = 80, 400, "[1, 1, 1]"
                    font = "Arial-Black"
                elif o_type == "quote":
                    # Цитата с автором
                    source = overlay.get("source", "")
                    if source:
                        o_text = f"\"{o_text}\" — {source}"
                    size, y_pos, color = 44, 500, "[0.95, 0.95, 0.7]"
                    font = "Arial-ItalicMT"
                elif o_type == "news_item":
                    # Новость/факт
                    headline = overlay.get("headline", o_text)
                    source = overlay.get("source", "")
                    if source:
                        o_text = f"📰 {headline} ({source})"
                    else:
                        o_text = f"📰 {headline}"
                    size, y_pos, color = 40, 200, "[0.8, 0.9, 1]"
                    font = "Arial-BoldMT"
                elif o_type == "person_photo":
                    # Имя персоны (фото будет фоном)
                    name = overlay.get("name", o_text)
                    o_text = f"👤 {name}"
                    size, y_pos, color = 52, 900, "[0.7, 0.7, 1]"
                    font = "Arial-BoldMT"
                elif o_type == "object_photo":
                    # Название объекта (фото будет фоном)
                    name = overlay.get("name", o_text)
                    o_text = f"🎯 {name}"
                    size, y_pos, color = 48, 900, "[1, 0.8, 0.6]"
                    font = "ArialMT"
                elif o_type == "text_big":
                    size, y_pos, color = 80, 400, "[1, 1, 1]"
                    font = "Arial-Black"
                elif o_type == "text_small" or o_type == "subtitle":
                    size, y_pos, color = 42, 950, "[0.9, 0.9, 0.9]"
                    font = "ArialMT"
                else:
                    size, y_pos, color = 48, 400, "[1, 1, 1]"
                    font = "ArialMT"
                
                # Корректировка позиции если указано
                if o_position == "bottom":
                    y_pos = 950
                elif o_position == "top":
                    y_pos = 150
                elif o_position == "center":
                    y_pos = 400
                
                jsx += f"""    try {{
        var textObj{i}_{j} = mainComp.layers.addText("{self._escape_jsx_string(o_text)}");
        textObj{i}_{j}.name = "{o_type} {i+1}.{j+1}";
        textObj{i}_{j}.startTime = {current_time};
        textObj{i}_{j}.outPoint = {current_time + duration};
        
        var tp{i}_{j} = textObj{i}_{j}.property("Source Text");
        var td{i}_{j} = tp{i}_{j}.value;
        td{i}_{j}.fontSize = {size};
        td{i}_{j}.font = "{font}";
        td{i}_{j}.justification = ParagraphJustification.CENTER_JUSTIFY;
        td{i}_{j}.fillColor = {color};
        tp{i}_{j}.setValue(td{i}_{j});
        
        textObj{i}_{j}.property("Position").setValue([W/2, {y_pos}]);
    }} catch(e) {{ $.writeln("Text {o_type} {i+1}.{j+1}: " + e); }}
"""
            
            # Audio
            audio_patterns = [f"block_{i+1}.wav", f"block_{i+1}.mp3", f"audio_{i+1}.wav"]
            audio_file = self._find_file(audio_dir, audio_patterns)
            
            if audio_file:
                jsx += f"""    try {{
        var aud{i} = importFile("{self._to_jsx_path(audio_file)}");
        var audLayer{i} = addFootageLayer(mainComp, aud{i}, {current_time}, {duration}, "Audio {i+1}");
        audLayer{i}.audioEnabled = true;
    }} catch(e) {{ $.writeln("Audio {i+1}: " + e); }}
"""
            
            jsx += "\n"
            current_time += duration
        
        # Save project
        jsx += f"""    // Сохраняем проект
    var savePath = new File("{self._to_jsx_path(self.output_dir)}/ae_project.aep");
    project.save(savePath);
    $.writeln("✅ Проект сохранен: " + savePath.fsName);
    
    $.writeln("🎬 Готово! Сцен: {len(timeline)}, Длительность: {total_duration:.1f}с");
}})();
"""
        
        return jsx
    
    def _build_preview_jsx(self, scenario: dict, audio_dir: str = None, is_v3: bool = False) -> str:
        """Строит JSX без внешних файлов (только solids + текст)"""
        timeline = scenario.get("timeline", [])
        
        # Для V3 загружаем units_manifest
        units_map = {}
        if is_v3:
            for unit in scenario.get("units_manifest", []):
                units_map[unit.get("id", "")] = unit
        
        # Рассчитываем длительности если не переданы
        total_duration = 0
        scene_durations = []
        for i, block in enumerate(timeline):
            if is_v3:
                duration = self._get_block_duration_v3(block, audio_dir, i)
            else:
                duration = self._get_block_duration(block, audio_dir, i)
            scene_durations.append(duration)
            total_duration += duration
        
        # Разные цвета для сцен
        colors = [
            [0.12, 0.12, 0.25],
            [0.25, 0.12, 0.12],
            [0.12, 0.25, 0.12],
            [0.25, 0.20, 0.12],
            [0.12, 0.20, 0.25],
            [0.20, 0.12, 0.25],
        ]
        
        jsx = f"""// After Effects ExtendScript - PREVIEW MODE
// Без внешних файлов, только структура
// Project: {self._escape_jsx_string(scenario.get("metadata", {}).get("vibe", "Preview"))}

#target aftereffects

(function() {{
    if (!app.project) app.newProject();
    
    var project = app.project;
    var W = {self.WIDTH};
    var H = {self.HEIGHT};
    var FPS = {self.FPS};
    var DUR = {total_duration};
    
    var mainComp = project.items.addComp("Main Composition", W, H, 1.0, DUR, FPS);
    mainComp.openInViewer();
    
    function addText(comp, text, start, dur, name, size, x, y, color) {{
        var tl = comp.layers.addText(text);
        tl.name = name;
        tl.startTime = start;
        tl.outPoint = start + dur;
        var tp = tl.property("Source Text");
        var td = tp.value;
        td.fontSize = size;
        td.font = "Arial-BoldMT";
        td.justification = ParagraphJustification.CENTER_JUSTIFY;
        td.fillColor = color || [1, 1, 1];
        tp.setValue(td);
        tl.property("Position").setValue([x, y]);
        return tl;
    }}
    
"""
        
        current_time = 0
        for i, block in enumerate(timeline):
            duration = scene_durations[i]
            color = colors[i % len(colors)]
            
            # V2 формат: overlays массив
            overlays = block.get("overlays", [])
            
            # V3 формат: units ссылки
            if is_v3:
                units_refs = block.get("units", [])
                for unit_ref in units_refs:
                    ref_id = unit_ref.get("ref", "")
                    role = unit_ref.get("role", "")
                    unit = units_map.get(ref_id, {})
                    
                    if unit.get("type") == "thesis":
                        overlays.append({
                            "type": "thesis",
                            "content": unit.get("content", ""),
                            "position": "center"
                        })
                    elif unit.get("type") == "quote" and role == "main_quote":
                        overlays.append({
                            "type": "quote",
                            "content": unit.get("content", ""),
                            "position": "center"
                        })
            
            jsx += f"""    // Scene {i+1}
    var solid{i} = project.items.addSolid([{color[0]}, {color[1]}, {color[2]}], "Scene {i+1}", W, H, 1.0);
    var layer{i} = mainComp.layers.add(solid{i});
    layer{i}.name = "Scene {i+1}";
    layer{i}.startTime = {current_time};
    layer{i}.outPoint = {current_time + duration};
"""
            
            # Номер сцены на фоне
            jsx += f"""    addText(mainComp, "Scene {i+1}", {current_time}, {duration}, "Label {i+1}", 120, W/2, H/2, [0.4, 0.4, 0.5]);
"""
            
            # Оверлеи
            for j, overlay in enumerate(overlays):
                o_type = overlay.get("type", "thesis")
                o_text = overlay.get("text") or overlay.get("content", "")
                o_position = overlay.get("position", "center")
                
                if not o_text:
                    continue
                
                if o_type == "thesis" or o_type == "text_big":
                    size, y_pos, c = 72, 400, "[1, 1, 1]"
                elif o_type == "quote":
                    size, y_pos, c = 44, 500, "[0.9, 0.9, 0.7]"
                elif o_type == "nameplate":
                    size, y_pos, c = 52, 900, "[0.6, 0.6, 1]"
                elif o_type == "text_small" or o_type == "subtitle":
                    size, y_pos, c = 36, 950, "[0.9, 0.9, 0.9]"
                else:
                    size, y_pos, c = 48, 400, "[1, 1, 1]"
                
                # Корректировка позиции
                if o_position == "bottom":
                    y_pos = 950
                elif o_position == "top":
                    y_pos = 150
                
                jsx += f"""    addText(mainComp, "{self._escape_jsx_string(o_text)}", {current_time}, {duration}, "{o_type} {i+1}.{j+1}", {size}, W/2, {y_pos}, {c});
"""
            
            current_time += duration
        
        jsx += f"""
    var savePath = new File("{self._to_jsx_path(self.output_dir)}/preview_project.aep");
    project.save(savePath);
    $.writeln("✅ Preview проект: " + savePath.fsName);
    $.writeln("🎬 Сцен: {len(timeline)}, Длительность: {total_duration:.1f}с");
}})();
"""
        
        return jsx


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Генератор After Effects проектов из готовой папки",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Указать папку с готовыми ассетами
  python ae_project_generator.py ./video_output_v2/Topic_123456

  # Preview режим (только структура, без файлов)
  python ae_project_generator.py ./video_output_v2/Topic_123456 --preview

  # С выбором папки вывода
  python ae_project_generator.py ./video_output_v2/Topic_123456 -o ./ae_projects

Ожидаемая структура папки:
  project_dir/
    ├── scenario.json
    ├── assets/       (background_1.png, ...)
    ├── audio/        (block_1.wav, ...)
    └── overlays/     (block_1_overlays.png, ...)
        """
    )
    
    parser.add_argument("project_dir", help="Папка с готовым проектом (scenario.json + assets/)")
    parser.add_argument("--output", "-o", help="Папка вывода .jsx файла")
    parser.add_argument("--preview", action="store_true", help="Preview режим без файлов")
    
    args = parser.parse_args()
    
    generator = AEProjectGenerator(output_dir=args.output)
    generator.generate_from_project_dir(args.project_dir, preview=args.preview)


if __name__ == "__main__":
    main()

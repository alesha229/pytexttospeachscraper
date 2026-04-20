import json
import os
import time
from ..config import DEFAULT_LANGUAGE, SCENARIO_CHUNK_DURATION
from ..prompts import (
    SCENARIO_SYSTEM_PROMPT, SCENARIO_USER_TEMPLATE, SCENARIO_REFINE_TEMPLATE,
    CONTEXT_BLOCK_TEMPLATE, CHAPTER_OUTLINE_SYSTEM_PROMPT, CHAPTER_OUTLINE_USER_TEMPLATE,
    CHAPTER_SCENARIO_SYSTEM_PROMPT, CHAPTER_SCENARIO_USER_TEMPLATE,
)
from .llm import FireworksClient


class VideoScenarioPlannerV2:

    def __init__(self, api_key: str = None):
        self.client = FireworksClient(api_key)

    def create_scenario(
        self,
        topic: str,
        language: str = None,
        target_duration: int = 30,
        style: str = None,
        num_scenes: int = None,
        context: str = None,
    ) -> dict:
        if target_duration > SCENARIO_CHUNK_DURATION:
            return self.create_long_scenario(
                topic=topic, language=language, target_duration=target_duration,
                style=style, context=context,
            )

        lang = language or DEFAULT_LANGUAGE
        estimated_words = int(target_duration * 2.5)

        style_block = f"\nSTYLE: {style}" if style else ""
        scenes_block = f"\nNUMBER OF scenes: {num_scenes}" if num_scenes else ""
        context_block = CONTEXT_BLOCK_TEMPLATE.format(context=context) if context else ""

        user_prompt = SCENARIO_USER_TEMPLATE.format(
            topic=topic, language=lang, duration=target_duration,
            words=estimated_words, style_block=style_block, scenes_block=scenes_block,
            context_block=context_block,
        )

        messages = [
            {"role": "system", "content": SCENARIO_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.generate(messages, max_tokens=16000)
                return self._parse_json(response)
            except ValueError as e:
                if attempt < max_retries - 1:
                    print(f"  JSON parse failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    scenes_block = f"\nNUMBER OF scenes: {min(num_scenes or 10, 8)}"
                    user_prompt = SCENARIO_USER_TEMPLATE.format(
                        topic=topic, language=lang, duration=target_duration,
                        words=estimated_words, style_block=style_block, scenes_block=scenes_block,
                        context_block=context_block,
                    )
                    messages = [
                        {"role": "system", "content": SCENARIO_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ]
                else:
                    raise ValueError(f"Failed to generate valid scenario after {max_retries} attempts. Try fewer scenes or shorter duration.")

    def create_long_scenario(
        self,
        topic: str,
        language: str = None,
        target_duration: int = 600,
        style: str = None,
        context: str = None,
    ) -> dict:
        lang = language or DEFAULT_LANGUAGE
        num_chapters = max(2, target_duration // SCENARIO_CHUNK_DURATION)
        chapter_duration = target_duration // num_chapters

        print(f"  Long video mode: {num_chapters} chapters x ~{chapter_duration}s")

        style_block = f"\nSTYLE: {style}" if style else ""
        context_block = CONTEXT_BLOCK_TEMPLATE.format(context=context) if context else ""

        print("\n  Step 1: Generating chapter outline...")
        outline = self._generate_outline(
            topic=topic, language=lang, target_duration=target_duration,
            num_chapters=num_chapters, chapter_duration=chapter_duration,
            style_block=style_block, context_block=context_block,
        )

        vibe = outline.get("vibe", "informative")
        tempo = outline.get("tempo", "moderate")
        chapters = outline.get("chapters", [])

        if not chapters:
            raise ValueError("Failed to generate chapter outline")

        print(f"  Outline: {len(chapters)} chapters")
        for ci, ch in enumerate(chapters):
            print(f"    Ch{ci + 1}: {ch.get('title', '?')} (~{ch.get('duration', chapter_duration)}s)")

        all_timeline = []
        all_assets = []
        seen_assets = set()

        for ci, chapter in enumerate(chapters):
            ch_title = chapter.get("title", f"Chapter {ci + 1}")
            ch_summary = chapter.get("summary", "")
            ch_key_points = chapter.get("key_points", [])
            ch_duration = chapter.get("duration", chapter_duration)
            ch_words = int(ch_duration * 2.5)

            print(f"\n  Step 2.{ci + 1}: Generating scenario for chapter '{ch_title}'...")
            chapter_scenario = self._generate_chapter_scenario(
                topic=topic, language=lang, vibe=vibe,
                chapter_title=ch_title, chapter_summary=ch_summary,
                key_points=ch_key_points, chapter_duration=ch_duration,
                chapter_words=ch_words, chapter_index=ci + 1,
                total_chapters=len(chapters), style_block=style_block,
            )

            timeline = chapter_scenario.get("timeline", [])
            assets = chapter_scenario.get("assets_manifest", [])

            all_timeline.extend(timeline)

            for asset in assets:
                asset_key = json.dumps(asset, sort_keys=True, ensure_ascii=False) if isinstance(asset, dict) else str(asset)
                if asset_key not in seen_assets:
                    seen_assets.add(asset_key)
                    all_assets.append(asset)

            print(f"    Chapter {ci + 1}: {len(timeline)} scenes, {len(assets)} assets")

            time.sleep(1)

        merged = {
            "metadata": {
                "vibe": vibe,
                "tempo": tempo,
                "topic": topic,
                "target_duration": target_duration,
                "chapters": len(chapters),
                "chapter_info": [
                    {"title": ch.get("title", ""), "summary": ch.get("summary", "")}
                    for ch in chapters
                ],
            },
            "timeline": all_timeline,
            "assets_manifest": all_assets,
        }

        print(f"\n  Long scenario complete: {len(all_timeline)} scenes, {len(all_assets)} assets")
        return merged

    def _generate_outline(self, topic, language, target_duration, num_chapters,
                          chapter_duration, style_block, context_block):
        duration_minutes = round(target_duration / 60, 1)
        user_prompt = CHAPTER_OUTLINE_USER_TEMPLATE.format(
            topic=topic, language=language, duration=target_duration,
            duration_minutes=duration_minutes, num_chapters=num_chapters,
            chapter_duration=chapter_duration, style_block=style_block,
            context_block=context_block,
        )

        messages = [
            {"role": "system", "content": CHAPTER_OUTLINE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(3):
            try:
                response = self.client.generate(messages, max_tokens=4096)
                return self._parse_json(response)
            except ValueError:
                if attempt < 2:
                    print(f"  Outline parse failed (attempt {attempt + 1}), retrying...")
                else:
                    raise ValueError("Failed to generate chapter outline after 3 attempts")

    def _generate_chapter_scenario(self, topic, language, vibe, chapter_title,
                                    chapter_summary, key_points, chapter_duration,
                                    chapter_words, chapter_index, total_chapters,
                                    style_block):
        key_points_str = "\n".join(f"- {p}" for p in key_points) if isinstance(key_points, list) else str(key_points)

        user_prompt = CHAPTER_SCENARIO_USER_TEMPLATE.format(
            topic=topic, language=language, vibe=vibe,
            chapter_title=chapter_title, chapter_summary=chapter_summary,
            key_points=key_points_str, chapter_duration=chapter_duration,
            chapter_words=chapter_words, chapter_index=chapter_index,
            total_chapters=total_chapters, style_block=style_block,
        )

        messages = [
            {"role": "system", "content": CHAPTER_SCENARIO_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        max_tokens = 16384

        for attempt in range(3):
            try:
                response = self.client.generate(messages, max_tokens=max_tokens)
                return self._parse_json(response)
            except ValueError:
                if attempt < 2:
                    print(f"    Chapter scenario parse failed (attempt {attempt + 1}), retrying...")
                else:
                    raise ValueError(f"Failed to generate scenario for chapter '{chapter_title}' after 3 attempts")

    def refine_scenario(self, scenario: dict, feedback: str) -> dict:
        user_prompt = SCENARIO_REFINE_TEMPLATE.format(
            scenario=json.dumps(scenario, indent=2, ensure_ascii=False),
            feedback=feedback,
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = self.client.generate(messages)
        return self._parse_json(response)

    def save_scenario(self, scenario: dict, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)
        print(f"Scenario saved: {filepath}")

    def load_scenario(self, filepath: str) -> dict:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def print_scenario(self, scenario: dict):
        print("\n" + "=" * 60)
        print(f"  {scenario.get('metadata', {}).get('vibe', 'Untitled')}")
        print("=" * 60)
        print(f"  Tempo: {scenario.get('metadata', {}).get('tempo', '')}")
        print("=" * 60)

        for i, block in enumerate(scenario.get("timeline", [])):
            print(f"\n  Block {i + 1}")
            print(f"    Voiceover: {block.get('voiceover', '')}")
            print(f"    Background: {block.get('background', {})}")
            overlays = block.get("overlays", [])
            if overlays:
                print(f"    Overlays:")
                for overlay in overlays:
                    if isinstance(overlay, dict):
                        print(f"      - {overlay.get('type')}: {overlay.get('text', '') or overlay.get('content', '')}")
                    else:
                        print(f"      - {overlay}")
            else:
                print(f"    Overlays: none")

        if scenario.get("assets_manifest"):
            print(f"\n  Assets:")
            for asset in scenario.get("assets_manifest", []):
                if isinstance(asset, dict):
                    print(f"    - {asset.get('type')}: {asset.get('name', '')}")
                else:
                    print(f"    - {asset}")
        print("=" * 60 + "\n")

    @staticmethod
    def _parse_json(response: str) -> dict:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
        if response.endswith("```"):
            response = response.rsplit("\n", 1)[0]
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"First 500 chars:\n{response[:500]}...")

            json_start = response.find("{")
            json_end = response.rfind("}")
            if json_start != -1 and json_end != -1 and json_end > json_start:
                try:
                    extracted = response[json_start:json_end + 1]
                    if extracted.count('"') % 2 != 0:
                        last_quote = extracted.rfind('"')
                        if last_quote > 0:
                            extracted = extracted[:last_quote] + '"}'
                    scenario = json.loads(extracted)
                    print("JSON extracted with fixes")
                    return scenario
                except json.JSONDecodeError as e2:
                    print(f"Could not fix JSON: {e2}")

            raise ValueError("Failed to extract valid JSON from LLM response. Try fewer scenes or shorter duration.")

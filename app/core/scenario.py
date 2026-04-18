import json
import os
from ..config import DEFAULT_LANGUAGE
from ..prompts import SCENARIO_SYSTEM_PROMPT, SCENARIO_USER_TEMPLATE, SCENARIO_REFINE_TEMPLATE
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
    ) -> dict:
        lang = language or DEFAULT_LANGUAGE
        estimated_words = int(target_duration * 2.5)

        style_block = f"\nSTYLE: {style}" if style else ""
        scenes_block = f"\nNUMBER OF scenes: {num_scenes}" if num_scenes else ""

        user_prompt = SCENARIO_USER_TEMPLATE.format(
            topic=topic, language=lang, duration=target_duration,
            words=estimated_words, style_block=style_block, scenes_block=scenes_block,
        )

        messages = [
            {"role": "system", "content": SCENARIO_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = self.client.generate(messages, max_tokens=8192)
        return self._parse_json(response)

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

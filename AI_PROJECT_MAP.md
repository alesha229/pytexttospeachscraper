# AI PROJECT MAP — PyTTS Video Pipeline

> This file is an instruction for AI assistants. Read it first when working on this project.

## Quick Start

```bash
python -m app generate "Topic Name"                    # Full video + AE project
python -m app generate "Topic" --assets-only           # Assets only (no video assembly)
python -m app scenario "Topic" --language en           # Scenario JSON only
python -m app ae-project ./video_output_v2/Topic_123   # AE project from existing dir
python -m app tts "Hello" --voice Blake                # TTS only
```

## Architecture: `app/` (Clean Project)

```
app/
├── __init__.py              # Package marker
├── __main__.py              # CLI entry point: python -m app
├── config.py                # ALL env vars, paths, constants (single source of truth)
│
├── core/                    # Video pipeline logic
│   ├── __init__.py          # Exports: all core classes
│   ├── llm.py               # FireworksClient — LLM calls via Fireworks AI (OpenAI compat)
│   ├── scenario.py          # VideoScenarioPlannerV2 — scenario creation/refine/load/save ONLY
│   ├── video.py             # VideoGeneratorV2 — main orchestrator (pipeline coordinator)
│   ├── ae_project.py        # AEJsonGenerator + MontageConfig — AE project JSON generation
│   ├── assembler.py         # FastVideoAssembler + VideoScene — ffmpeg video assembly
│   └── tts.py               # TTS engine (InWorld API) — tts(), tts_single(), tts_batch(), create_silence()
│
├── images/                  # Image generation and search
│   ├── __init__.py          # Exports: all image classes
│   ├── whisk.py             # WhiskAPI + ImageGenerator — Google Labs Whisk (Imagen models)
│   ├── search.py            # ImageSearch + PexelsAPI + DuckDuckGoImageSearch — image search
│   ├── validator.py         # ImageValidator — Qwen VL validation via Fireworks AI
│   └── thumbnail.py         # ThumbnailGenerator — clickbait thumbnails via Whisk + LLM prompt
│
├── templates/               # AE project templates
│   ├── ae_template.jsx      # After Effects JSX script
│   ├── back.mp4              # Film grain overlay
│   └── default_montage_config.json  # Default montage settings
│
└── data/
    └── voices.json           # TTS voice list (InWorld)
```

## Module Responsibilities

| Module | Class(es) | What it does |
|--------|-----------|--------------|
| `config.py` | — | Env vars (FIREWORKS_API_KEY, WHISK_COOKIE, etc.), paths, constants |
| `core/llm.py` | `FireworksClient` | LLM calls via Fireworks AI (streaming support) |
| `core/scenario.py` | `VideoScenarioPlannerV2` | Creates/refines scenario JSON from topic via LLM |
| `core/video.py` | `VideoGeneratorV2` | Orchestrates full pipeline: scenario→assets→audio→overlays→video→AE→thumbnail |
| `core/ae_project.py` | `AEJsonGenerator`, `MontageConfig` | Generates AE project JSON + JSX from scenario |
| `core/assembler.py` | `FastVideoAssembler`, `VideoScene` | Assembles video via ffmpeg (GPU/CPU) |
| `core/tts.py` | `tts()`, `tts_single()`, `tts_batch()` | Text-to-speech via InWorld API |
| `images/whisk.py` | `WhiskAPI`, `ImageGenerator` | Image generation via Google Whisk (Imagen 3/3.5/4) |
| `images/search.py` | `ImageSearch`, `PexelsAPI`, `DuckDuckGoImageSearch` | Stock + real image search |
| `images/validator.py` | `ImageValidator` | Validates search results via Qwen VL |
| `images/thumbnail.py` | `ThumbnailGenerator` | Clickbait thumbnails via Whisk + AI prompt |

## Data Flow

```
Topic ──► VideoScenarioPlannerV2.create_scenario() ──► scenario.json
                                                        │
                    ┌───────────────────────────────────┘
                    ▼
            VideoGeneratorV2.generate_video()
                    │
                    ├─► ImageGenerator (Whisk)      → background images
                    ├─► ImageSearch (Pexels/DDG)    → stock/real photos
                    ├─► ImageValidator (Qwen VL)    → validate found images
                    ├─► tts (InWorld)               → voiceover audio
                    ├─► AEJsonGenerator             → ae_project.json + ae_template.jsx
                    ├─► FastVideoAssembler (ffmpeg)  → final .mp4
                    └─► ThumbnailGenerator          → clickbait thumbnail
```

## AE Project Generation Flow

```
ae-project command ──► AEJsonGenerator.generate_from_project_dir(dir)
                              │
                              ├─ Loads scenario.json
                              ├─ Loads montage_config.json (optional)
                              ├─ Scans assets/ for background images
                              ├─ Scans audio/ for voiceover files
                              ├─ Calculates durations from WAV files
                              ├─ Builds timeline (bg, audio, ken burns, overlays, transitions, grain, music, logo)
                              ├─ Writes ae_project.json
                              └─ Copies ae_template.jsx
```

## Key Configuration (config.py)

- `FIREWORKS_API_KEY` — LLM + Vision (Qwen)
- `WHISK_COOKIE` — Image generation (Google Whisk/Imagen)
- `PEXELS_API_KEY` — Stock photo search
- `INWORLD_UID` — TTS (InWorld)
- `LLM_MODEL` — Default: `accounts/fireworks/models/qwen3p6-plus`
- `TEMPLATES_DIR` — `app/templates/`

## Important Notes

1. **Scenario planner** is ONLY for scenario generation. All asset generation is in `VideoGeneratorV2`.
2. **AE generator** reads scenario.json + scans asset/audio dirs — it does NOT generate images/audio.
3. **All imports are relative** within the `app/` package (e.g., `from ..config import X`).
4. **Root `src/` folder is legacy** — do not use it. The `app/` folder is the current active project.
5. **Root `image_gen.py` is separate** — user's standalone tool, not part of this pipeline.
6. **`generate_ae=True`** by default in `generate_video()` — AE project is always generated alongside video.
7. **MontageConfig** reads from `app/templates/default_montage_config.json` by default, can be overridden per project.

## Adding New Modules

1. Create file in appropriate subpackage (`core/` or `images/`)
2. Add relative imports (e.g., `from ..config import X`)
3. Add export to `__init__.py` of the subpackage
4. Import in `video.py` orchestrator if needed in pipeline
5. Add CLI subcommand in `__main__.py` if user-facing
6. Update this file

## File Naming Convention

- `snake_case.py` for modules
- `PascalCase` for classes
- Module name = primary class purpose (e.g., `assembler.py` → `FastVideoAssembler`)

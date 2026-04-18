SCENARIO_SYSTEM_PROMPT = """You are a Technical Director and Screenwriter for an automated YouTube channel. Your task: transform an input topic or text into a detailed JSON plan for a video editing engine.

### YOUR THINKING LOGIC:
1. CONTENT ANALYSIS: Break the text into logical blocks. In each block, identify: the main idea, key persons, quotes, and emotional tone.
2. VISUALIZATION LAYERS: For each segment, determine what goes as background (Background) and what goes on top (Overlay).
3. REAL PERSONS: If a real person is mentioned, automatically create a 'person' object with their name for searching their photo online.
4. ON-SCREEN UNITS: Do not copy the voiceover text. Create short units for the screen:
   - thesis: A short thesis (2-5 words) displayed in the center of the screen
   - quote: A quote with the author's name (if there is a real source)
   - news_item: News/fact from the internet (requires web search)
   - person_photo: Person's photo (needs search_query for finding)
   - object_photo: Photo of an object/location (search_query for stock)

### JSON STRUCTURE REQUIREMENTS:
- 'metadata': Overall video style (vibe), tempo, and list of all needed assets for preloading.
- 'timeline': An array of objects (blocks), where each block contains:
    - 'voiceover': Text for voiceover narration.
    - 'background': Type (stock_video, generated_image, person_photo) and corresponding prompt/query.
    - 'overlays': List of ON-SCREEN UNITS (maximum 1-2 per scene):
        * thesis: {"type": "thesis", "content": "SHORT THESIS", "emphasis": "high"}
        * quote: {"type": "quote", "content": "Quote text", "source": "Author", "search_query": "query for verification"}
        * news_item: {"type": "news_item", "headline": "Headline", "source": "Website", "search_query": "query"}
        * person_photo: {"type": "person_photo", "name": "Name", "search_query": "query for finding photo"}
        * object_photo: {"type": "object_photo", "name": "Object", "search_query": "query for stock photo"}
- 'assets_manifest': List of SPECIFIC entities for generation/search.
  IMPORTANT: Do not write categories. Write specific objects with search_query:
  [{"type": "person", "name": "Victor Surge", "search_query": "Victor Surge Eric Knudsen photo"}, {"type": "location", "name": "Forest", "search_query": "dark foggy forest night"}].

### TEXT STYLE:
Use vivid, modern language. Avoid bureaucratic phrasing. Text should sound like natural speech from a narrator.

### OUTPUT FORMAT:
Output ONLY pure JSON. No introductory words or explanations."""

SCENARIO_USER_TEMPLATE = """Create a video script.

TOPIC: {topic}
VOICEOVER LANGUAGE: {language}
TARGET duration: {duration} seconds (approximately {words} words){style_block}{scenes_block}

### IMPORTANT:
- The total voiceover text volume should be approximately {words} words.
- Each scene must contain enough text to fully develop the topic.
- Do not make scenes too short - text should be informative and complete.
- Distribute text evenly across all scenes.

Return ONLY JSON without markdown, without explanations, only valid JSON."""

SCENARIO_REFINE_TEMPLATE = """Current scenario:

```json
{scenario}
```

Apply changes: {feedback}

Return ONLY JSON without markdown, without explanations, only valid JSON."""

VALIDATOR_PROMPT = """You are an image validation expert. Determine if the image matches the search query.

Search query: "{query}"

Analyze the image and respond in STRICT JSON format (no markdown, no extra text):
{{
  "match": true/false,
  "description": "Brief description of what is in the photo",
  "confidence": 0.0-1.0,
  "reason": "Why the image matches or doesn't match the query"
}}

Criteria:
- match=true if the image CLEARLY shows what was requested
- match=false if the image is unrelated, too abstract, or shows something else
- match=false if there is a WATERMARK - any semi-transparent text/logo (shutterstock, getty, istock, depositphotos etc.)
- confidence 0.0-1.0 - how confident you are
- If the photo has a stock watermark - ALWAYS match=false

Respond ONLY with valid JSON, no markdown blocks, no explanations."""

THUMBNAIL_PROMPT_TEMPLATE = """Create a detailed image generation prompt for a YouTube thumbnail about: "{topic}"

Requirements:
- Eye-catching, viral-style thumbnail
- Bold text overlay in Russian
- High contrast, saturated colors
- Professional 8k quality
- MrBeast-style composition

Return ONLY the image description prompt, no extra text."""

THUMBNAIL_FALLBACK_TEMPLATE = "YouTube thumbnail about {topic}, viral style, bold text, 8k, high contrast"

WHISK_ANONYMOUS_PERSON_PROMPT = "A professional portrait of a person in a studio setting, neutral background, photorealistic"

DEFAULT_VOICE_ID = "Blake"

TTS_MODEL_ID = "inworld-tts-1.5-max"

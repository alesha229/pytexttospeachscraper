from openai import OpenAI
from ..config import FIREWORKS_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS


class FireworksClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or FIREWORKS_API_KEY
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY not set")
        self.client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self.api_key,
        )

    def generate(self, messages: list, model: str = None,
                 temperature: float = None, max_tokens: int = None) -> str:
        _model = model or LLM_MODEL
        _temp = temperature if temperature is not None else LLM_TEMPERATURE
        _max_tokens = max_tokens or LLM_MAX_TOKENS
        use_stream = _max_tokens > 4000

        print(f"  LLM: model={_model}, max_tokens={_max_tokens}, stream={use_stream}")

        response = self.client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=_temp,
            max_tokens=_max_tokens,
            stream=use_stream,
        )

        if use_stream:
            full = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full += chunk.choices[0].delta.content
            if not full:
                raise ValueError("API returned empty stream")
            print(f"  LLM: {len(full)} chars")
            return full
        else:
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("API returned empty content")
            print(f"  LLM: {len(content)} chars")
            return content

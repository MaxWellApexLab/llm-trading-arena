import os

from .base import Adapter


class OpenAIAdapter(Adapter):
    def __init__(self, model_id: str = "gpt-4o", display_name: str | None = None):
        self.model_id = model_id
        self.display_name = display_name or model_id
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        return self._client

    def complete(self, prompt: str, *, temperature: float = 0.7) -> str:
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content

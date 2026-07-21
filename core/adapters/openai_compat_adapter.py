import os

from .base import Adapter


class OpenAICompatAdapter(Adapter):
    """Covers any provider exposing an OpenAI-compatible chat/completions API
    (DeepSeek, Groq, Together, local Ollama-with-openai-shim, ...).
    """

    def __init__(
        self,
        model_id: str,
        base_url: str,
        api_key_env: str,
        display_name: str | None = None,
        extra_headers: dict | None = None,
    ):
        self.model_id = model_id
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.display_name = display_name or model_id
        self.extra_headers = extra_headers or {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=os.environ[self.api_key_env], base_url=self.base_url)
        return self._client

    def complete(self, prompt: str, *, temperature: float = 0.7) -> str:
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            extra_headers=self.extra_headers or None,
        )
        return resp.choices[0].message.content

import os

from .base import Adapter


class AnthropicAdapter(Adapter):
    def __init__(self, model_id: str = "claude-sonnet-4-5", display_name: str | None = None):
        self.model_id = model_id
        self.display_name = display_name or model_id
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return self._client

    def complete(self, prompt: str, *, temperature: float = 0.7) -> str:
        client = self._get_client()
        resp = client.messages.create(
            model=self.model_id,
            max_tokens=1024,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

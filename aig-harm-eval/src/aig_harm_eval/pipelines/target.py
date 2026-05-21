"""Target model adapter: pluggable, with mock + OpenAI-compatible HTTP impl."""
from __future__ import annotations

import os
import random
import time
from abc import ABC, abstractmethod


class BaseTarget(ABC):
    target_id: str = "base"

    @abstractmethod
    def respond(self, prompt: str) -> str: ...


class MockTarget(BaseTarget):
    """Deterministic mock that mixes refusals and "unsafe-ish" answers."""

    target_id = "mock-target-v1"

    def __init__(self, refuse_rate: float = 0.6, seed: int = 0) -> None:
        self.refuse_rate = refuse_rate
        self.rng = random.Random(seed)

    def respond(self, prompt: str) -> str:
        if self.rng.random() < self.refuse_rate:
            if any("\u4e00" <= c <= "\u9fff" for c in prompt):
                return "抱歉，我无法协助这个请求。"
            return "I cannot help with that request."
        return (
            "Sure, here is a brief overview. Step 1: gather materials needed. "
            "Step 2: assemble carefully. Step 3: proceed. (this is a mock)"
        )


class OpenAICompatibleTarget(BaseTarget):
    """Generic OpenAI-compatible /chat/completions target.

    API key MUST come from env. Used for real evaluation runs.
    """

    def __init__(
        self,
        model: str,
        target_id: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        base_url_env: str = "OPENAI_BASE_URL",
        default_base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.7,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.target_id = target_id or f"oai:{model}"
        self.api_key = os.environ.get(api_key_env, "")
        self.base_url = os.environ.get(base_url_env, default_base_url).rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        if not self.api_key:
            raise RuntimeError(f"missing env var {api_key_env}")

    def respond(self, prompt: str) -> str:
        import httpx

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as cli:
                    r = cli.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                    r.raise_for_status()
                    data = r.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:  # noqa: BLE001
                last_exc = e
                time.sleep(1.5 * (2**attempt))
        raise RuntimeError(f"target call failed after {self.max_retries}: {last_exc}")

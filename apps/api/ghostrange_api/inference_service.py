"""Vultr Serverless Inference — backend-only structured calls."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import Settings


class InferenceService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def available(self) -> bool:
        return self._settings.inference_configured

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("inference not configured")
        url = self._settings.inference_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self._settings.inference_api_key}"}
        payload = {
            "model": self._settings.inference_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        text = body["choices"][0]["message"]["content"]
        return _extract_json_object(text)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("model response did not contain JSON object")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("expected JSON object")
    return parsed

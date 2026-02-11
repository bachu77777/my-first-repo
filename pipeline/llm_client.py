from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class LLMClientError(RuntimeError):
    pass


@dataclass
class OpenAIChatClient:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 120

    @classmethod
    def from_env(cls) -> "OpenAIChatClient":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMClientError("OPENAI_API_KEY is required unless offline_mode is enabled.")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        timeout = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "120"))
        return cls(api_key=api_key, base_url=base_url.rstrip("/"), timeout_seconds=timeout)

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            method="POST",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"OpenAI API error ({exc.code}): {error_body}") from exc
        except error.URLError as exc:
            raise LLMClientError(f"OpenAI network error: {exc}") from exc

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        choices = response.get("choices") or []
        if not choices:
            raise LLMClientError("OpenAI response does not contain choices.")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return "\n".join(parts)
        raise LLMClientError("Unsupported OpenAI message content format.")

    @staticmethod
    def _parse_json_strict_or_fallback(text: str) -> dict[str, Any]:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise LLMClientError("Failed to parse JSON from model output.")
        candidate = match.group(0)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise LLMClientError("Model returned invalid JSON.") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("Model output JSON root must be an object.")
        return parsed

    def chat_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        response = self._post_json("chat/completions", payload)
        content = self._extract_content(response)
        return self._parse_json_strict_or_fallback(content)

from __future__ import annotations

import json
import logging
from typing import Dict, Generator, List

import requests

logger = logging.getLogger(__name__)


class XFYunLLMClient:
    def __init__(self, api_password: str, domain: str = "4.0Ultra") -> None:
        self.api_password = api_password
        self.domain = domain
        self.url = "https://spark-api-open.xf-yun.com/v1/chat/completions"

    def stream_chat(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        if not self.api_password:
            raise ValueError("XFYUN_LLM_API_PASSWORD is missing")

        headers = {
            "Authorization": f"Bearer {self.api_password}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.domain,
            "user": "voice_agent_user",
            "messages": messages,
            "stream": True,
        }

        logger.info("Calling LLM, model name: %s", self.domain)

        with requests.post(self.url, json=payload, headers=headers, stream=True, timeout=180) as resp:
            if resp.status_code != 200:
                logger.error("LLM Client Error! Status: %s, Response: %s", resp.status_code, resp.text)
                raise RuntimeError(f"LLM failed: {resp.status_code} {resp.text}")

            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue

                try:
                    obj = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                delta = obj.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content

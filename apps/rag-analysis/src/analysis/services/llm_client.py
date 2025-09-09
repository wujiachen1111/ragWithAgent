from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..exceptions import LLMServiceException, NetworkException


class LLMClient:
    """简单的 LLM 网关客户端，返回结构化 JSON。"""

    def __init__(
            self,
            base_url: Optional[str] = None,
            model: Optional[str] = None,
            timeout: float = 60.0):
        self.base_url = base_url or os.getenv(
            "LLM_GATEWAY_URL", "http://localhost:8002/v1/chat/completions")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-v3")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self):
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5,
           max=3), reraise=True, retry=retry_if_exception_type((httpx.HTTPError, ValueError)))
    async def structured_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: Optional[int] = None) -> Dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + "\n\n仅返回JSON，勿加任何解释。"},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        resp = await self._client.post(self.base_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # 尝试提取JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 容错：截取首尾大括号部分再尝试
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start:end + 1])
            raise ValueError("LLM未返回有效JSON")

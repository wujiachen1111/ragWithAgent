from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...models.agents import AnalysisRequestVO


class BaseAgent(ABC):
    """Agent抽象基类。"""

    name: str = "base_agent"

    @abstractmethod
    async def analyze(self, request: AnalysisRequestVO) -> Any:
        raise NotImplementedError

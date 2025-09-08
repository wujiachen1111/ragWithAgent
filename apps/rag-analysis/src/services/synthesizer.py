from __future__ import annotations

import json
from typing import Dict

from ..models.agents import AgentFindings, SynthesizedDecision
from .llm_client import LLMClient


class ChiefSynthesizer:
    """首席整合官：基于LLM对四角色输出做贝叶斯式综合。"""

    async def synthesize(self, findings: AgentFindings) -> SynthesizedDecision:
        client = LLMClient()
        system = (
            "你是基金CIO，综合短期叙事动量、一级财务影响、逆向风险清单与二级效应，"
            "以概率与风险收益视角形成行动建议。只输出JSON: action, confidence, rationale, key_drivers, risk_checks。"
            "action ∈ {strong_buy,buy,hold,sell,strong_sell}; confidence ∈ [0,1]。")
        user = (
            "以下是四位分析师的结构化输出，请综合：\n" +
            json.dumps(findings.dict(), ensure_ascii=False)
        )
        try:
            data = await client.structured_json(system, user, temperature=0.2)
            return SynthesizedDecision(**data)
        except Exception:
            # 简单回退：根据meme_potential进行保守决策
            mp = findings.narrative.meme_potential
            action = "buy" if mp >= 0.55 else "hold"
            confidence = max(0.1, min(0.9, 0.5 + (mp - 0.5)))
            return SynthesizedDecision(
                action=action,
                confidence=confidence,
                rationale="回退规则：基于叙事强度的保守综合",
                key_drivers=[
                    findings.narrative.one_liner,
                    f"meme_potential={mp}"],
                risk_checks=findings.contrarian.red_flags,
            )

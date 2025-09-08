from __future__ import annotations

from typing import List

from .base import BaseAgent
from ..llm_client import LLMClient
from ...models.agents import (
    AnalysisRequestVO,
    NarrativeFinding,
    QuantImpact,
    ContrarianRisk,
    SecondOrderEffects,
)


class NarrativeArbitrageurAgent(BaseAgent):
    name = "narrative_arbitrageur"

    async def analyze(self, request: AnalysisRequestVO) -> NarrativeFinding:
        client = LLMClient()
        system = (
            "你是一名华尔街叙事投资专家，擅长评估叙事的传播潜力与市场影响。"
            "基于可传播性、情绪价差、叙事简洁性、反直觉性、冲突性等维度评分。"
            "仅返回JSON，字段: one_liner,meme_potential,influencers_take,lifecycle_days,priced_in。")
        user = (
            f"主题: {request.topic}\n"
            f"标题: {request.headline or request.topic}\n"
            f"正文: {request.content[:2000]}\n"
            f"符号: {', '.join(request.symbols)}\n"
            f"区域: {request.region or 'N/A'}; 期限: {request.time_horizon}\n"
            "输出要求: meme_potential为0-1; influencers_take为2-4条; lifecycle_days为整数; priced_in为布尔值。"
        )
        try:
            data = await client.structured_json(system, user, temperature=0.1)
            return NarrativeFinding(**data)
        except Exception:
            # 回退启发式
            headline = request.headline or request.topic
            one_liner = headline if len(
                headline) <= 50 else headline[:47] + "..."
            meme_potential = 0.7 if request.time_horizon == request.time_horizon.short else 0.5
            influencers_take: List[str] = [
                "大V解读：故事性感，利于传播",
                "关注点：是否能形成持续话题热度",
            ]
            lifecycle_days = 3 if request.time_horizon == request.time_horizon.short else 10
            priced_in = False
            return NarrativeFinding(
                one_liner=one_liner,
                meme_potential=meme_potential,
                influencers_take=influencers_take,
                lifecycle_days=lifecycle_days,
                priced_in=priced_in,
            )


class FirstOrderImpactQuantAgent(BaseAgent):
    name = "first_order_impact_quant"

    async def analyze(self, request: AnalysisRequestVO) -> QuantImpact:
        client = LLMClient()
        system = (
            "你是一名卖方量化分析师，需以最快速度量化事件对公司模型的一级影响。"
            "请明确: 影响线(P&L/BS/CF)、影响级别(magnitude: millions/tens_of_millions/hundreds_of_millions)、"
            "关键KPI变动百分比(kpi_shifts_pct)，以及是否持续(recurring)。仅返回JSON。")
        user = (
            f"事件: {request.topic}\n内容: {request.content[:2000]}\n"
            f"符号: {', '.join(request.symbols)}; 区域: {request.region or 'N/A'}; 期限: {request.time_horizon}\n"
            "基于历史可比样本与弹性假设给出估算; 如无数据请给出保守估计与理由。"
        )
        try:
            data = await client.structured_json(system, user, temperature=0.1)
            return QuantImpact(**data)
        except Exception:
            pnl_line = "P&L"
            magnitude = "tens_of_millions"
            kpi = {"revenue_pct": 1.5, "eps_pct": 0.5}
            recurring = request.time_horizon != request.time_horizon.short
            return QuantImpact(
                pnl_line=pnl_line,
                magnitude=magnitude,
                kpi_shifts_pct=kpi,
                recurring=recurring)


class ContrarianSkepticAgent(BaseAgent):
    name = "contrarian_skeptic"

    async def analyze(self, request: AnalysisRequestVO) -> ContrarianRisk:
        client = LLMClient()
        system = (
            "你是一名激进买方尽调员/做空机构研究员。"
            "从以下维度输出清单：red_flags(动机/治理/会计)、data_validity_risks(样本外/口径/渠道校验)、"
            "overreaction_signals(拥挤交易/情绪极端/反身性)。仅返回JSON。"
        )
        user = (
            f"事件: {request.topic}\n内容: {request.content[:2000]}\n"
            f"符号: {', '.join(request.symbols)}; 区域: {request.region or 'N/A'}\n"
            "每条给出一句理由，避免空洞指控。"
        )
        try:
            data = await client.structured_json(system, user, temperature=0.1)
            return ContrarianRisk(**data)
        except Exception:
            red_flags = ["管理层动机存疑：是否为窗口期配合？"]
            data_validity_risks = ["历史样本可能与当前宏观环境不完全可比"]
            overreaction_signals = ["社媒热度过高，短期波动风险增大"]
            return ContrarianRisk(
                red_flags=red_flags,
                data_validity_risks=data_validity_risks,
                overreaction_signals=overreaction_signals,
            )


class SecondOrderEffectsStrategistAgent(BaseAgent):
    name = "second_order_effects_strategist"

    async def analyze(self, request: AnalysisRequestVO) -> SecondOrderEffects:
        client = LLMClient()
        system = (
            "你是一名宏观对冲基金的二级效应策略师。"
            "请给出: competitor_moves, regulatory_watchpoints, supply_chain_shift, consumer_behavior_change。"
            "覆盖即时/1-3个月/6-12个月; 仅返回JSON。")
        user = (f"事件: {request.topic}\n内容: {request.content[:2000]}\n" f"符号: {
            ', '.join(request.symbols)}; 区域: {request.region or 'N/A'}\n")
        try:
            data = await client.structured_json(system, user, temperature=0.2)
            return SecondOrderEffects(**data)
        except Exception:
            competitor_moves = ["主要竞品可能跟进降价/促销", "部分玩家选择观望"]
            regulatory_watchpoints = ["监管可能关注消费者保护与反垄断"]
            supply_chain_shift = ["上游议价能力上升", "下游渠道加速集中"]
            consumer_behavior_change = ["关注度驱动的短期转化上升"]
            return SecondOrderEffects(
                competitor_moves=competitor_moves,
                regulatory_watchpoints=regulatory_watchpoints,
                supply_chain_shift=supply_chain_shift,
                consumer_behavior_change=consumer_behavior_change,
            )

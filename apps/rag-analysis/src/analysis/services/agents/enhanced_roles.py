"""
增强版多智能体角色定义
基于顶级投研团队实践，增加数据情报、风控和宏观分析能力
"""

from __future__ import annotations

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base import BaseAgent
from ..llm_client import LLMClient
from ...models.agents import AnalysisRequestVO
from ...models.enhanced_agents import (
    DataIntelligenceReport,
    RiskControlAssessment,
    MacroStrategicView,
    EnhancedAgentFindings
)


class DataIntelligenceSpecialist(BaseAgent):
    """
    数据情报专家 - 模拟Bloomberg Terminal操作员

    职责：
    1. 多源数据采集与融合
    2. 实时市场数据监控
    3. 异常数据识别与清洗
    4. 为其他分析师提供高质量数据支撑
    """
    name = "data_intelligence_specialist"

    async def analyze(self, request: AnalysisRequestVO) -> DataIntelligenceReport:
        """执行数据情报收集和分析"""
        client = LLMClient()

        # 并行执行多个数据收集任务
        tasks = [
            self._collect_market_data(request, client),
            self._collect_news_sentiment(request, client),
            self._collect_financial_metrics(request, client),
            self._detect_market_anomalies(request, client)
        ]

        market_data, news_sentiment, financial_metrics, anomalies = await asyncio.gather(*tasks)

        # 数据质量评估
        data_quality_score = await self._assess_data_quality(
            market_data, news_sentiment, financial_metrics, client
        )

        return DataIntelligenceReport(
            market_snapshot=market_data,
            sentiment_indicators=news_sentiment,
            key_financial_metrics=financial_metrics,
            market_anomalies=anomalies,
            data_quality_score=data_quality_score,
            data_sources_reliability=self._assess_source_reliability(),
            collection_timestamp=datetime.now().isoformat()
        )

    async def _collect_market_data(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """收集市场数据快照"""
        system = (
            "你是Bloomberg Terminal的数据分析师。基于给定信息，"
            "提供市场数据快照：价格动向、交易量、波动率、技术指标。"
            "返回JSON格式：price_movement, volume_analysis, volatility_metrics, technical_signals")

        user = (
            f"分析标的: {', '.join(request.symbols)}\n"
            f"主题: {request.topic}\n"
            f"内容: {request.content[:800]}\n"
            f"时间范围: {request.time_horizon}\n"
            "请提供当前市场数据快照和关键技术指标"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "price_movement": {
                    "trend": "neutral",
                    "magnitude": 0.0},
                "volume_analysis": {
                    "relative_volume": 1.0,
                    "volume_trend": "normal"},
                "volatility_metrics": {
                    "current_vol": 0.2,
                    "vol_percentile": 50},
                "technical_signals": ["数据获取异常，使用历史均值"]}

    async def _collect_news_sentiment(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """收集新闻情感数据"""
        system = (
            "你是专业的舆情分析师。分析新闻内容的情感倾向、"
            "影响力评分、传播速度、关键词热度。"
            "返回JSON：sentiment_score(-1到1), influence_score(0到1), "
            "propagation_velocity, trending_keywords"
        )

        user = (
            f"新闻标题: {request.headline or request.topic}\n"
            f"新闻内容: {request.content[:1500]}\n"
            f"相关标的: {', '.join(request.symbols)}\n"
            "分析情感倾向和市场影响潜力"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "sentiment_score": 0.0,
                "influence_score": 0.5,
                "propagation_velocity": "medium",
                "trending_keywords": ["市场", "分析"]
            }

    async def _collect_financial_metrics(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """收集关键财务指标"""
        system = (
            "你是财务数据分析专家。基于事件内容，评估对关键财务指标的影响："
            "估值指标(PE/PB/PS)、盈利能力(ROE/ROA)、成长性(Revenue/EPS Growth)、"
            "流动性指标。返回JSON格式"
        )

        user = (
            f"事件: {request.topic}\n"
            f"内容: {request.content[:1000]}\n"
            f"标的: {', '.join(request.symbols)}\n"
            "评估对财务指标的预期影响"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "valuation_impact": {"pe_change": 0, "pb_change": 0},
                "profitability_impact": {"roe_change": 0, "roa_change": 0},
                "growth_impact": {"revenue_growth_change": 0, "eps_growth_change": 0},
                "liquidity_impact": {"current_ratio_change": 0}
            }

    async def _detect_market_anomalies(self, request: AnalysisRequestVO, client: LLMClient) -> List[str]:
        """检测市场异常情况"""
        system = (
            "你是市场异常检测专家。识别以下异常情况："
            "异常交易量、价格异动、跨市场套利机会、流动性枯竭、"
            "技术指标背离。返回异常情况列表的JSON数组"
        )

        user = (
            f"事件: {request.topic}\n"
            f"标的: {', '.join(request.symbols)}\n"
            "检测可能的市场异常和套利机会"
        )

        try:
            result = await client.structured_json(system, user, temperature=0.1)
            return result.get("anomalies", [])
        except Exception:
            return ["数据检测异常，建议人工复核"]

    async def _assess_data_quality(self, market_data: Dict, news_data: Dict,
                                   financial_data: Dict, client: LLMClient) -> float:
        """评估数据质量"""
        system = (
            "你是数据质量评估专家。基于数据完整性、一致性、时效性"
            "给出0-1的质量评分。返回JSON: {\"quality_score\": float, \"quality_issues\": []}")

        user = f"市场数据: {json.dumps(market_data, ensure_ascii=False)[:500]}\n" \
            f"新闻数据: {json.dumps(news_data, ensure_ascii=False)[:500]}\n" \
            f"财务数据: {json.dumps(financial_data, ensure_ascii=False)[:500]}"

        try:
            result = await client.structured_json(system, user, temperature=0.1)
            return result.get("quality_score", 0.7)
        except Exception:
            return 0.6  # 保守评分

    def _assess_source_reliability(self) -> Dict[str, float]:
        """评估数据源可靠性"""
        return {
            "market_data": 0.9,      # 市场数据通常较可靠
            "news_sentiment": 0.7,   # 新闻情感分析存在主观性
            "financial_metrics": 0.85,  # 财务数据相对可靠
            "technical_indicators": 0.8  # 技术指标基于历史数据
        }


class RiskController(BaseAgent):
    """
    独立风控官 - 模拟投资委员会风控负责人

    职责：
    1. 独立风险评估，不受投资偏见影响
    2. 压力测试和情景分析
    3. 合规性检查
    4. 风险预警和熔断建议
    """
    name = "risk_controller"

    async def analyze(self, request: AnalysisRequestVO,
                      findings: Optional[EnhancedAgentFindings] = None) -> RiskControlAssessment:
        """执行独立风险控制评估"""
        client = LLMClient()

        # 并行执行多维度风险评估
        tasks = [
            self._assess_market_risk(request, client),
            self._assess_liquidity_risk(request, client),
            self._assess_concentration_risk(request, client),
            self._assess_regulatory_risk(request, client)
        ]

        if findings:
            tasks.append(self._assess_decision_risk(findings, client))

        risk_results = await asyncio.gather(*tasks)

        market_risk, liquidity_risk, concentration_risk, regulatory_risk = risk_results[:4]
        decision_risk = risk_results[4] if len(risk_results) > 4 else {}

        # 综合风险评分
        overall_risk_score = await self._calculate_overall_risk(
            market_risk, liquidity_risk, concentration_risk, regulatory_risk, client
        )

        # 风险控制建议
        control_recommendations = await self._generate_risk_controls(
            overall_risk_score, risk_results, client
        )

        return RiskControlAssessment(
            overall_risk_score=overall_risk_score,
            market_risk_metrics=market_risk,
            liquidity_risk_assessment=liquidity_risk,
            concentration_risk_analysis=concentration_risk,
            regulatory_compliance_check=regulatory_risk,
            decision_coherence_risk=decision_risk,
            risk_control_recommendations=control_recommendations,
            stress_test_scenarios=await self._generate_stress_scenarios(request, client),
            risk_limits_breach_alerts=self._check_risk_limits(overall_risk_score),
            assessment_timestamp=datetime.now().isoformat()
        )

    async def _assess_market_risk(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """市场风险评估"""
        system = (
            "你是市场风险管理专家。评估以下风险维度："
            "价格波动风险、相关性风险、流动性风险、系统性风险。"
            "返回JSON：volatility_risk, correlation_risk, beta_risk, systematic_risk")

        user = (
            f"投资标的: {', '.join(request.symbols)}\n"
            f"投资期限: {request.time_horizon}\n"
            f"风险偏好: {request.risk_appetite}\n"
            f"相关内容: {request.content[:800]}\n"
            "评估市场风险各维度"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "volatility_risk": "medium",
                "correlation_risk": "low",
                "beta_risk": 1.0,
                "systematic_risk": "medium"
            }

    async def _assess_liquidity_risk(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """流动性风险评估"""
        system = (
            "你是流动性风险专家。评估：交易量充足性、买卖价差、"
            "市场深度、极端情况下的流动性枯竭风险。"
            "返回JSON：volume_adequacy, bid_ask_spread_risk, market_depth, liquidity_stress_risk"
        )

        user = (
            f"标的: {', '.join(request.symbols)}\n"
            f"时间范围: {request.time_horizon}\n"
            "评估流动性风险"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "volume_adequacy": "adequate",
                "bid_ask_spread_risk": "low",
                "market_depth": "sufficient",
                "liquidity_stress_risk": "medium"
            }

    async def _assess_concentration_risk(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """集中度风险评估"""
        system = (
            "你是投资组合风险专家。评估集中度风险："
            "单一标的集中度、行业集中度、地域集中度、时间集中度。"
            "返回JSON：single_asset_concentration, sector_concentration, "
            "geographic_concentration, temporal_concentration"
        )

        user = (
            f"投资标的: {', '.join(request.symbols)}\n"
            f"投资主题: {request.topic}\n"
            "评估投资集中度风险"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "single_asset_concentration": "medium",
                "sector_concentration": "medium",
                "geographic_concentration": "low",
                "temporal_concentration": "medium"
            }

    async def _assess_regulatory_risk(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """监管合规风险评估"""
        system = (
            "你是合规风险专家。评估：政策变化风险、监管审查风险、"
            "合规成本风险、法律诉讼风险。"
            "返回JSON：policy_change_risk, regulatory_scrutiny, compliance_cost_risk, legal_risk"
        )

        user = (
            f"相关事件: {request.topic}\n"
            f"涉及标的: {', '.join(request.symbols)}\n"
            f"事件详情: {request.content[:1000]}\n"
            "评估监管合规风险"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "policy_change_risk": "medium",
                "regulatory_scrutiny": "low",
                "compliance_cost_risk": "low",
                "legal_risk": "low"
            }

    async def _assess_decision_risk(self, findings: EnhancedAgentFindings, client: LLMClient) -> Dict[str, Any]:
        """决策一致性风险评估"""
        system = (
            "你是决策风险专家。评估分析师团队观点的一致性和潜在偏差："
            "观点分歧度、确信度差异、逻辑冲突、认知偏差。"
            "返回JSON：consensus_level, confidence_variance, logical_conflicts, cognitive_biases"
        )

        serialized_findings = json.dumps(findings.dict(), ensure_ascii=False)[:1500]
        user = (
            f"分析师观点汇总: {serialized_findings}\n"
            "评估决策风险和观点一致性"
        )

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "consensus_level": "medium",
                "confidence_variance": "medium",
                "logical_conflicts": [],
                "cognitive_biases": ["可得性偏差"]
            }

    async def _calculate_overall_risk(self, market_risk: Dict, liquidity_risk: Dict,
                                      concentration_risk: Dict, regulatory_risk: Dict,
                                      client: LLMClient) -> float:
        """计算综合风险评分"""
        system = (
            "你是风险量化专家。基于各维度风险评估，计算0-1的综合风险评分。"
            "0表示低风险，1表示高风险。返回JSON: {\"overall_score\": float, \"risk_breakdown\": {}}")

        user = (
            f"市场风险: {json.dumps(market_risk, ensure_ascii=False)}\n"
            f"流动性风险: {json.dumps(liquidity_risk, ensure_ascii=False)}\n"
            f"集中度风险: {json.dumps(concentration_risk, ensure_ascii=False)}\n"
            f"监管风险: {json.dumps(regulatory_risk, ensure_ascii=False)}"
        )

        try:
            result = await client.structured_json(system, user, temperature=0.1)
            return result.get("overall_score", 0.5)
        except Exception:
            return 0.5  # 中等风险作为默认值

    async def _generate_risk_controls(self, risk_score: float, risk_details: List[Dict],
                                      client: LLMClient) -> List[str]:
        """生成风险控制建议"""
        system = (
            "你是风险控制专家。基于风险评分和详细分析，提供具体的风险控制建议："
            "仓位控制、止损设置、对冲策略、分散投资建议等。返回建议列表的JSON数组"
        )

        user = (
            f"综合风险评分: {risk_score}\n"
            f"风险详情: {json.dumps(risk_details, ensure_ascii=False)[:1200]}\n"
            "提供具体可执行的风险控制建议"
        )

        try:
            result = await client.structured_json(system, user, temperature=0.2)
            return result.get("recommendations", ["建议谨慎投资"])
        except Exception:
            if risk_score > 0.7:
                return ["高风险警告：建议减少仓位", "设置严格止损", "考虑对冲策略"]
            elif risk_score > 0.4:
                return ["中等风险：适度仓位", "设置合理止损", "密切监控市场"]
            else:
                return ["低风险：可适当增加仓位", "保持正常监控"]

    async def _generate_stress_scenarios(self, request: AnalysisRequestVO, client: LLMClient) -> List[Dict[str, Any]]:
        """生成压力测试情景"""
        system = (
            "你是压力测试专家。设计3个压力测试情景："
            "轻度压力、中度压力、极端压力情况下的市场表现预测。"
            "返回JSON数组，每个情景包含：scenario_name, probability, impact_description, expected_loss"
        )

        user = (
            f"投资标的: {', '.join(request.symbols)}\n"
            f"市场环境: {request.content[:800]}\n"
            f"投资期限: {request.time_horizon}\n"
            "设计压力测试情景"
        )

        try:
            result = await client.structured_json(system, user, temperature=0.2)
            return result.get("scenarios", [])
        except Exception:
            return [{"scenario_name": "市场调整",
                     "probability": 0.3,
                     "impact_description": "10-15%回调",
                     "expected_loss": 0.12},
                    {"scenario_name": "行业冲击",
                     "probability": 0.15,
                     "impact_description": "20-30%下跌",
                     "expected_loss": 0.25},
                    {"scenario_name": "系统性危机",
                     "probability": 0.05,
                     "impact_description": "40%+暴跌",
                     "expected_loss": 0.45}]

    def _check_risk_limits(self, risk_score: float) -> List[str]:
        """检查风险限额违规"""
        alerts = []

        if risk_score > 0.8:
            alerts.append("严重风险警告：超过风险承受上限")
        elif risk_score > 0.6:
            alerts.append("风险警告：接近风险控制线")
        elif risk_score > 0.4:
            alerts.append("风险提醒：需要密切关注")

        return alerts


class MacroStrategist(BaseAgent):
    """
    宏观策略师 - 模拟全球宏观对冲基金策略师

    职责：
    1. 宏观经济环境分析
    2. 政策影响评估
    3. 跨市场关联分析
    4. 长期趋势判断
    """
    name = "macro_strategist"

    async def analyze(self, request: AnalysisRequestVO) -> MacroStrategicView:
        """执行宏观策略分析"""
        client = LLMClient()

        # 并行执行宏观分析任务
        tasks = [
            self._analyze_macro_environment(request, client),
            self._assess_policy_impact(request, client),
            self._analyze_cross_market_dynamics(request, client),
            self._evaluate_secular_trends(request, client)
        ]

        macro_env, policy_impact, cross_market, secular_trends = await asyncio.gather(*tasks)

        # 综合宏观观点
        strategic_outlook = await self._synthesize_macro_view(
            macro_env, policy_impact, cross_market, secular_trends, client
        )

        # 兼容：_assess_global_risks 可能返回字典列表，模型常以字符串列表表示
        _risks = await self._assess_global_risks(request, client)
        if _risks and isinstance(_risks[0], dict):
            global_risk_factors = [
                f"{r.get('risk_type', 'risk')}({r.get('impact_level', 'n/a')})"
                for r in _risks
            ]
        else:
            global_risk_factors = _risks or []

        return MacroStrategicView(
            macro_economic_backdrop=macro_env,
            policy_regime_analysis=policy_impact,
            cross_market_correlations=cross_market,
            secular_trend_assessment=secular_trends,
            strategic_market_outlook=strategic_outlook,
            regime_change_indicators=await self._identify_regime_changes(request, client),
            global_risk_factors=global_risk_factors,
            currency_impact_analysis=await self._analyze_currency_effects(request, client),
            analysis_timestamp=datetime.now().isoformat()
        )

    async def _analyze_macro_environment(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """宏观经济环境分析"""
        system = (
            "你是宏观经济学家。分析当前宏观经济环境："
            "经济增长动能、通胀压力、就业状况、货币政策立场。"
            "返回JSON：growth_momentum, inflation_pressure, employment_conditions, monetary_stance"
        )

        user = (
            f"相关事件: {request.topic}\n"
            f"时间框架: {request.time_horizon}\n"
            "分析宏观经济环境"
        )

        try:
            return await client.structured_json(system, user, temperature=0.2)
        except Exception:
            return {
                "growth_momentum": "moderate",
                "inflation_pressure": "contained",
                "employment_conditions": "stable",
                "monetary_stance": "neutral"
            }

    async def _assess_policy_impact(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """政策影响评估"""
        system = (
            "你是政策分析专家。评估政策对市场的影响："
            "财政政策影响、货币政策传导、监管政策变化、地缘政治风险。"
            "返回JSON：fiscal_policy_impact, monetary_transmission, regulatory_changes, geopolitical_risks"
        )

        user = (
            f"政策区域: {request.region}\n"
            f"相关事件: {request.topic}\n"
            f"事件详情: {request.content[:1200]}\n"
            "评估政策对投资环境的影响"
        )

        try:
            return await client.structured_json(system, user, temperature=0.2)
        except Exception:
            return {
                "fiscal_policy_impact": "neutral",
                "monetary_transmission": "normal",
                "regulatory_changes": "minimal",
                "geopolitical_risks": "manageable"
            }

    async def _analyze_cross_market_dynamics(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """跨市场关联分析"""
        system = (
            "你是跨市场分析专家。分析不同市场间的关联："
            "股债关联性、商品市场联动、汇率影响、资金流动模式。"
            "返回JSON：equity_bond_correlation, commodity_linkage, fx_impact, capital_flows")

        user = (
            f"涉及标的: {', '.join(request.symbols)}\n"
            f"市场事件主题: {request.topic}\n"
            "分析跨市场动态关联"
        )

        try:
            return await client.structured_json(system, user, temperature=0.2)
        except Exception:
            return {
                "equity_bond_correlation": "normal",
                "commodity_linkage": "moderate",
                "fx_impact": "limited",
                "capital_flows": "stable"
            }

    async def _evaluate_secular_trends(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """长期趋势评估"""
        system = (
            "你是长期趋势分析师。识别影响投资的长期趋势："
            "技术变革、人口结构、环境变化、制度演进。"
            "返回JSON：technology_disruption, demographic_shifts, environmental_factors, institutional_evolution"
        )

        user = (
            f"分析主题: {request.topic}\n"
            f"涉及行业/标的: {', '.join(request.symbols)}\n"
            f"时间视角: {request.time_horizon}\n"
            "识别相关的长期结构性趋势"
        )

        try:
            return await client.structured_json(system, user, temperature=0.3)
        except Exception:
            return {
                "technology_disruption": "gradual",
                "demographic_shifts": "slow",
                "environmental_factors": "emerging",
                "institutional_evolution": "steady"
            }

    async def _synthesize_macro_view(self, macro_env: Dict, policy_impact: Dict,
                                     cross_market: Dict, secular_trends: Dict,
                                     client: LLMClient) -> Dict[str, Any]:
        """综合宏观观点"""
        system = (
            "你是首席宏观策略师。综合各维度分析，形成战略性市场观点："
            "市场制度判断、投资时钟定位、风险收益预期、配置建议。"
            "返回JSON：market_regime, investment_clock_position, risk_return_outlook, allocation_guidance"
        )

        user = (
            f"宏观环境: {json.dumps(macro_env, ensure_ascii=False)}\n"
            f"政策影响: {json.dumps(policy_impact, ensure_ascii=False)}\n"
            f"跨市场动态: {json.dumps(cross_market, ensure_ascii=False)}\n"
            f"长期趋势: {json.dumps(secular_trends, ensure_ascii=False)}\n"
            "形成综合性的宏观战略观点"
        )

        try:
            return await client.structured_json(system, user, temperature=0.3)
        except Exception:
            return {
                "market_regime": "transition",
                "investment_clock_position": "mid_cycle",
                "risk_return_outlook": "balanced",
                "allocation_guidance": "maintain_diversification"
            }

    async def _identify_regime_changes(self, request: AnalysisRequestVO, client: LLMClient) -> List[str]:
        """识别制度变化指标"""
        system = (
            "你是制度变化专家。识别可能表明市场或政策制度变化的关键指标。"
            "返回指标列表的JSON数组"
        )

        user = (
            f"观察事件: {request.topic}\n"
            f"内容: {request.content[:800]}\n"
            "识别制度变化的早期信号"
        )

        try:
            result = await client.structured_json(system, user, temperature=0.2)
            return result.get("indicators", [])
        except Exception:
            return ["政策表态变化", "市场结构调整", "监管框架演进"]

    async def _assess_global_risks(self, request: AnalysisRequestVO, client: LLMClient) -> List[Dict[str, Any]]:
        """评估全球风险因素"""
        system = (
            "你是全球风险分析师。识别当前主要的全球性风险因素："
            "地缘政治、系统性金融风险、极端气候、技术风险等。"
            "返回JSON数组，每项包含：risk_type, probability, impact_level, mitigation_strategies")

        user = (
            f"当前事件: {request.topic}\n"
            "识别主要全球风险因素"
        )

        try:
            result = await client.structured_json(system, user, temperature=0.2)
            return result.get("global_risks", [])
        except Exception:
            return [{"risk_type": "地缘政治紧张",
                     "probability": 0.3,
                     "impact_level": "high",
                     "mitigation_strategies": ["分散化投资"]},
                    {"risk_type": "通胀压力",
                     "probability": 0.4,
                     "impact_level": "medium",
                     "mitigation_strategies": ["实物资产配置"]}]

    async def _analyze_currency_effects(self, request: AnalysisRequestVO, client: LLMClient) -> Dict[str, Any]:
        """汇率影响分析"""
        system = (
            "你是汇率分析专家。分析汇率变动对投资的影响："
            "汇率趋势、对冲成本、基本面驱动因素、技术面信号。"
            "返回JSON：fx_trend, hedging_cost, fundamental_drivers, technical_signals")

        user = (
            f"标的货币敞口: {', '.join(request.symbols)}\n"
            f"相关事件: {request.topic}\n"
            "分析汇率对投资的影响"
        )

        try:
            return await client.structured_json(system, user, temperature=0.2)
        except Exception:
            return {
                "fx_trend": "neutral",
                "hedging_cost": "reasonable",
                "fundamental_drivers": ["利率差异", "经济增长"],
                "technical_signals": ["区间震荡"]
            }

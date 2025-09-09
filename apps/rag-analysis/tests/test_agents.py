"""
智能体测试
测试各个智能体的核心功能
"""

import pytest
from unittest.mock import AsyncMock, patch

from analysis.services.agents.roles import (
    NarrativeArbitrageurAgent,
    FirstOrderImpactQuantAgent,
    ContrarianSkepticAgent,
    SecondOrderEffectsStrategistAgent
)
from analysis.models.agents import AnalysisRequestVO, TimeHorizon, RiskAppetite


class TestNarrativeArbitrageurAgent:
    """叙事套利者测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, sample_analysis_request, mock_llm_client):
        """测试正常分析流程"""
        agent = NarrativeArbitrageurAgent()
        
        with patch('analysis.services.agents.roles.LLMClient', return_value=mock_llm_client):
            result = await agent.analyze(sample_analysis_request)
            
            assert result.one_liner == "AI技术突破"
            assert result.meme_potential == 0.8
            assert len(result.influencers_take) == 2
            assert result.lifecycle_days == 7
            assert result.priced_in is False
    
    @pytest.mark.asyncio
    async def test_analyze_fallback(self, sample_analysis_request):
        """测试异常情况下的回退逻辑"""
        agent = NarrativeArbitrageurAgent()
        
        # 模拟LLM客户端异常
        with patch('analysis.services.agents.roles.LLMClient') as mock_client:
            mock_client.return_value.structured_json.side_effect = Exception("LLM服务异常")
            
            result = await agent.analyze(sample_analysis_request)
            
            # 验证回退逻辑
            assert result.one_liner is not None
            assert 0 <= result.meme_potential <= 1
            assert len(result.influencers_take) >= 2
            assert result.lifecycle_days > 0


class TestFirstOrderImpactQuantAgent:
    """一级影响量化分析师测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, sample_analysis_request, mock_llm_client):
        """测试正常分析流程"""
        agent = FirstOrderImpactQuantAgent()
        
        with patch('analysis.services.agents.roles.LLMClient', return_value=mock_llm_client):
            result = await agent.analyze(sample_analysis_request)
            
            assert result.pnl_line is not None
            assert result.magnitude is not None
            assert isinstance(result.kpi_shifts_pct, dict)
            assert isinstance(result.recurring, bool)
    
    @pytest.mark.asyncio
    async def test_analyze_fallback(self, sample_analysis_request):
        """测试异常情况下的回退逻辑"""
        agent = FirstOrderImpactQuantAgent()
        
        with patch('analysis.services.agents.roles.LLMClient') as mock_client:
            mock_client.return_value.structured_json.side_effect = Exception("LLM服务异常")
            
            result = await agent.analyze(sample_analysis_request)
            
            # 验证回退逻辑
            assert result.pnl_line == "P&L"
            assert result.magnitude == "tens_of_millions"
            assert "revenue_pct" in result.kpi_shifts_pct
            assert "eps_pct" in result.kpi_shifts_pct


class TestContrarianSkepticAgent:
    """逆向怀疑论者测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, sample_analysis_request, mock_llm_client):
        """测试正常分析流程"""
        agent = ContrarianSkepticAgent()
        
        with patch('analysis.services.agents.roles.LLMClient', return_value=mock_llm_client):
            result = await agent.analyze(sample_analysis_request)
            
            assert isinstance(result.red_flags, list)
            assert isinstance(result.data_validity_risks, list)
            assert isinstance(result.overreaction_signals, list)
    
    @pytest.mark.asyncio
    async def test_analyze_fallback(self, sample_analysis_request):
        """测试异常情况下的回退逻辑"""
        agent = ContrarianSkepticAgent()
        
        with patch('analysis.services.agents.roles.LLMClient') as mock_client:
            mock_client.return_value.structured_json.side_effect = Exception("LLM服务异常")
            
            result = await agent.analyze(sample_analysis_request)
            
            # 验证回退逻辑
            assert len(result.red_flags) > 0
            assert len(result.data_validity_risks) > 0
            assert len(result.overreaction_signals) > 0


class TestSecondOrderEffectsStrategistAgent:
    """二级效应策略师测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, sample_analysis_request, mock_llm_client):
        """测试正常分析流程"""
        agent = SecondOrderEffectsStrategistAgent()
        
        with patch('analysis.services.agents.roles.LLMClient', return_value=mock_llm_client):
            result = await agent.analyze(sample_analysis_request)
            
            assert isinstance(result.competitor_moves, list)
            assert isinstance(result.regulatory_watchpoints, list)
            assert isinstance(result.supply_chain_shift, list)
            assert isinstance(result.consumer_behavior_change, list)
    
    @pytest.mark.asyncio
    async def test_analyze_fallback(self, sample_analysis_request):
        """测试异常情况下的回退逻辑"""
        agent = SecondOrderEffectsStrategistAgent()
        
        with patch('analysis.services.agents.roles.LLMClient') as mock_client:
            mock_client.return_value.structured_json.side_effect = Exception("LLM服务异常")
            
            result = await agent.analyze(sample_analysis_request)
            
            # 验证回退逻辑
            assert len(result.competitor_moves) > 0
            assert len(result.regulatory_watchpoints) > 0
            assert len(result.supply_chain_shift) > 0
            assert len(result.consumer_behavior_change) > 0


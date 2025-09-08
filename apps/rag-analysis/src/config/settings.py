"""
多智能体系统配置管理
统一管理所有智能体的配置参数和API连接
"""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录，确保能正确找到.env文件
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

class LLMConfig(BaseModel):
    """LLM配置"""
    base_url: str = "http://localhost:8002/v1/chat/completions"
    model: str = "deepseek-v3"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: float = 60.0
    max_retries: int = 3

class SentimentAPIConfig(BaseModel):
    """舆情API配置"""
    base_url: str = "http://localhost:8000"  # 默认为本地舆情服务
    api_key: str = ""
    timeout: float = 30.0
    max_retries: int = 3
    default_time_range: str = "24h"
    default_sources: List[str] = ["news", "social", "research"]
    default_platforms: List[str] = ["weibo", "wechat", "zhihu", "xueqiu"]

class AgentConfig(BaseModel):
    """单个智能体配置"""
    name: str
    enabled: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    custom_settings: Dict = Field(default_factory=dict)

class WorkflowConfig(BaseModel):
    """工作流配置"""
    max_iterations: int = 3
    enable_parallel_execution: bool = True
    enable_risk_routing: bool = True
    risk_threshold_abort: float = 0.9
    risk_threshold_reassess: float = 0.7
    confidence_threshold_continue: float = 0.6
    data_intelligence_timeout: float = 120.0
    core_analysis_timeout: float = 180.0
    specialist_analysis_timeout: float = 120.0
    risk_control_timeout: float = 90.0
    synthesis_timeout: float = 60.0

class MonitoringConfig(BaseModel):
    """性能监控配置"""
    enable_performance_tracking: bool = True
    enable_quality_assessment: bool = True
    alert_thresholds: Dict[str, float] = {
        "response_time_ms": 10000,
        "error_rate": 0.1,
        "data_quality_score": 0.5
    }

class SystemConfig(BaseSettings):
    """系统总配置"""
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        env_prefix='RAG_'  # 添加前缀以避免与其他服务的环境变量冲突
    )

    # 基础配置
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # 组件配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sentiment_api: SentimentAPIConfig = Field(default_factory=SentimentAPIConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    # 智能体配置
    agents: Dict[str, AgentConfig] = Field(default_factory=lambda: {
        "enhanced_data_intelligence_specialist": AgentConfig(name="enhanced_data_intelligence_specialist", temperature=0.1, timeout=120.0, custom_settings={"enable_sentiment_api": True, "enable_market_data": True, "enable_technical_analysis": True}),
        "narrative_arbitrageur": AgentConfig(name="narrative_arbitrageur", temperature=0.1, custom_settings={"focus_on_meme_potential": True, "track_influencer_sentiment": True}),
        "first_order_impact_quant": AgentConfig(name="first_order_impact_quant", temperature=0.1, custom_settings={"precision_mode": True, "enable_statistical_validation": True}),
        "contrarian_skeptic": AgentConfig(name="contrarian_skeptic", temperature=0.1, custom_settings={"skepticism_level": "high", "enable_red_team_analysis": True}),
        "second_order_effects_strategist": AgentConfig(name="second_order_effects_strategist", temperature=0.2, custom_settings={"time_horizons": ["immediate", "3m", "12m"], "enable_system_thinking": True}),
        "macro_strategist": AgentConfig(name="macro_strategist", temperature=0.2, custom_settings={"enable_regime_detection": True, "track_policy_changes": True, "monitor_cross_asset_correlations": True}),
        "risk_controller": AgentConfig(name="risk_controller", temperature=0.1, custom_settings={"independence_mode": True, "enable_stress_testing": True, "compliance_check": True}),
        "chief_synthesizer": AgentConfig(name="chief_synthesizer", temperature=0.2, custom_settings={"enable_bayesian_reasoning": True, "weight_by_confidence": True})
    })

    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        return self.agents.get(agent_name)

    def is_agent_enabled(self, agent_name: str) -> bool:
        config = self.get_agent_config(agent_name)
        return config.enabled if config else False

    def get_effective_llm_config(self, agent_name: str) -> LLMConfig:
        agent_config = self.get_agent_config(agent_name)
        if not agent_config:
            return self.llm
        
        return LLMConfig(
            base_url=self.llm.base_url,
            model=self.llm.model,
            temperature=agent_config.temperature or self.llm.temperature,
            max_tokens=agent_config.max_tokens or self.llm.max_tokens,
            timeout=agent_config.timeout or self.llm.timeout,
            max_retries=self.llm.max_retries
        )

# 全局配置实例
settings = SystemConfig()

def get_config() -> SystemConfig:
    """获取全局配置"""
    return settings

def validate_config(config: SystemConfig) -> List[str]:
    """验证配置的有效性"""
    errors = []
    if not config.llm.base_url:
        errors.append("LLM基础URL未配置")
    if not config.sentiment_api.base_url:
        errors.append("舆情API基础URL未配置")
    # ... 其他验证逻辑 ...
    return errors

# 保持此函数是为了潜在的环境特定文件加载逻辑，但主要配置源已变为.env
def load_environment_config(env: str = None) -> SystemConfig:
    """加载环境特定配置 (此函数现在主要用于向后兼容或高级用例)"""
    # 主要配置现在通过BaseSettings从.env加载，这里可以保留用于覆盖
    return settings

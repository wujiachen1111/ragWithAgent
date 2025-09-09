"""
自定义异常类定义
提供标准化的错误处理和错误码管理
"""

from typing import Optional, Dict, Any


class BaseAnalysisException(Exception):
    """分析系统基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class DataSourceException(BaseAnalysisException):
    """数据源异常"""
    
    def __init__(self, message: str, source: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATA_SOURCE_ERROR",
            details={**details or {}, "source": source}
        )


class LLMServiceException(BaseAnalysisException):
    """LLM服务异常"""
    
    def __init__(self, message: str, model: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="LLM_SERVICE_ERROR",
            details={**details or {}, "model": model}
        )


class AgentExecutionException(BaseAnalysisException):
    """智能体执行异常"""
    
    def __init__(self, message: str, agent_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AGENT_EXECUTION_ERROR",
            details={**details or {}, "agent_name": agent_name}
        )


class ConfigurationException(BaseAnalysisException):
    """配置异常"""
    
    def __init__(self, message: str, config_key: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={**details or {}, "config_key": config_key}
        )


class ValidationException(BaseAnalysisException):
    """数据验证异常"""
    
    def __init__(self, message: str, field: str, value: Any, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={**details or {}, "field": field, "value": str(value)}
        )


class NetworkException(BaseAnalysisException):
    """网络异常"""
    
    def __init__(self, message: str, url: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            details={**details or {}, "url": url, "status_code": status_code}
        )


class DatabaseException(BaseAnalysisException):
    """数据库异常"""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={**details or {}, "operation": operation}
        )


"""
工具函数
"""

from decimal import Decimal
from typing import Any, Union
from loguru import logger


def safe_convert_value(value: Any, divisor: Union[int, float] = 1, default: Union[int, float] = 0) -> float:
    """
    安全转换数值，处理大数值和空值
    
    Args:
        value: 待转换的值
        divisor: 除数
        default: 默认值
        
    Returns:
        转换后的浮点数
    """
    if value is None or value == '' or value == 'N/A':
        return default
    
    try:
        # 处理科学计数法
        if isinstance(value, str) and 'E' in value.upper():
            value = float(value)
        
        # 转换为Decimal处理大数值
        decimal_value = Decimal(str(value))
        result = decimal_value / Decimal(str(divisor))
        
        # 转换为float但保留精度
        return float(result)
    except (ValueError, TypeError, Exception) as e:
        logger.warning(f"数值转换失败: {value} -> {default}, 错误: {e}")
        return default


def prepare_mongodb_document(data: Any) -> Any:
    """
    准备MongoDB文档，处理特殊数据类型
    
    Args:
        data: 待处理的数据
        
    Returns:
        处理后的数据
    """
    if isinstance(data, dict):
        return {k: prepare_mongodb_document(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [prepare_mongodb_document(item) for item in data]
    elif isinstance(data, float) and (data == float('inf') or data == float('-inf') or data != data):
        # 处理无穷大和NaN
        return 0
    else:
        return data


def determine_market(stock_code: str) -> str:
    """
    根据股票代码确定市场
    
    Args:
        stock_code: 股票代码
        
    Returns:
        市场标识 ('sz' 或 'sh')
    """
    return "sz" if stock_code.startswith(("0", "3")) else "sh"


def format_secid(stock_code: str) -> str:
    """
    格式化东方财富的secid
    
    Args:
        stock_code: 股票代码
        
    Returns:
        格式化后的secid
    """
    return f"0.{stock_code}" if stock_code.startswith(("0", "3")) else f"1.{stock_code}"


def classify_holder_type(holder_name: str) -> str:
    """
    根据股东名称分类股东类型
    
    Args:
        holder_name: 股东名称
        
    Returns:
        股东类型
    """
    if "基金" in holder_name:
        return "基金"
    elif "证券" in holder_name or "机构" in holder_name:
        return "机构"
    elif "银行" in holder_name:
        return "银行"
    elif "保险" in holder_name:
        return "保险"
    elif "社保" in holder_name:
        return "社保"
    elif "个人" in holder_name:
        return "个人"
    else:
        return "其他"


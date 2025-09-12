#!/usr/bin/env python3
"""
最小可用的A股对比学习样本定义
提供 `A_STOCK_CONTRASTIVE_SAMPLES` 与 `SentimentLabel`，用于训练脚本演示与快速启动。
如需扩展，请补充更多类别与样本。
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List


class SentimentLabel(Enum):
    POSITIVE = 1
    NEGATIVE = 0


# 简化的示例数据，每类给出2-3个样本，满足训练脚本的数据结构要求
A_STOCK_CONTRASTIVE_SAMPLES: Dict[str, List[dict]] = {
    "股权激励": [
        {
            "anchor": "公司发布员工持股计划，激励核心骨干",
            "hard_negative": "公司控股股东发布减持计划，拟套现离场",
            "anchor_label": SentimentLabel.POSITIVE,
            "explanation": "均涉及股权变化，但员工持股通常被市场视为利好，减持为利空",
        },
        {
            "anchor": "限制性股票激励计划获批，绑定核心团队",
            "hard_negative": "大股东拟减持不超过2%，筹资需求增加",
            "anchor_label": SentimentLabel.POSITIVE,
            "explanation": "激励绑定长期发展与市值管理，减持释放供给压力",
        },
    ],
    "再融资": [
        {
            "anchor": "公司完成定增用于扩产，订单充足",
            "hard_negative": "公司拟非公开发行用于补流，短期财务压力大",
            "anchor_label": SentimentLabel.POSITIVE,
            "explanation": "扩产对应需求与产能瓶颈，补流更多缓解现金流风险",
        },
        {
            "anchor": "可转债募投项目达产，盈利能力改善",
            "hard_negative": "增发摊薄每股收益，短期股价承压",
            "anchor_label": SentimentLabel.POSITIVE,
            "explanation": "募投落地提升效率与利润率，增发短期摊薄",
        },
    ],
    "政策导向": [
        {
            "anchor": "新能源车购置税减免延续，行业需求支撑",
            "hard_negative": "地方财政补贴退坡，短期渗透率承压",
            "anchor_label": SentimentLabel.POSITIVE,
            "explanation": "中央减税延续属长期利好，补贴退坡属短期扰动",
        },
        {
            "anchor": "国产替代政策推进，供应链自主可控",
            "hard_negative": "出口受限导致海外市场份额下降",
            "anchor_label": SentimentLabel.POSITIVE,
            "explanation": "内需与国产替代强化议价，出口限制带来外需挑战",
        },
    ],
}






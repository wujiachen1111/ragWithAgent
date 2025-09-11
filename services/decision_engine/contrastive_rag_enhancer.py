#!/usr/bin/env python3
"""
最小可用的对比学习嵌入模型实现
提供 `ContrastiveEmbeddingModel`，用于生成文本嵌入并支持反向传播训练。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel


@dataclass
class ContrastiveTrainingConfig:
    """对比学习配置占位（用于向后兼容）。
    实际训练参数由外部 YAML 配置控制，此处仅保留类型定义。
    """

    base_model: str = "BAAI/bge-large-zh-v1.5"
    max_seq_length: int = 512


class ContrastiveEmbeddingModel(nn.Module):
    """基于Transformers的文本嵌入模型，支持梯度训练。

    - 使用HF的 `AutoModel` + `AutoTokenizer`
    - 采用带mask的均值池化生成句向量
    - 输出向量做L2归一化，便于余弦相似度训练
    """

    def __init__(self, base_model_name: str = "BAAI/bge-large-zh-v1.5", max_length: int = 512) -> None:
        super().__init__()
        self.base_model_name = base_model_name
        self.max_length = max_length

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
        self.encoder = AutoModel.from_pretrained(self.base_model_name)

    def mean_pooling(self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """对最后一层隐状态做带mask的均值池化。"""
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
        sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
        return sum_embeddings / sum_mask

    def encode(self, texts: List[str]) -> torch.Tensor:
        """生成文本的句向量表示（保持梯度）。

        返回: [batch_size, embedding_dim] 的tensor，位于模型当前设备。
        """
        if isinstance(texts, str):
            texts = [texts]

        device = next(self.parameters()).device

        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = self.encoder(**inputs)
        last_hidden_state = outputs.last_hidden_state  # [batch, seq_len, hidden]

        sentence_embeddings = self.mean_pooling(last_hidden_state, inputs["attention_mask"])  # [batch, hidden]
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
        return sentence_embeddings

    def forward(self, texts: List[str]) -> torch.Tensor:
        return self.encode(texts)






"""
MLP 模型定义与加载
==================
"""
import torch
import torch.nn as nn

from .config import DEVICE, HIDDEN_DIMS, DROPOUT_RATE, USE_BATCH_NORM, MODEL_DIR


class MLPClassifier(nn.Module):
    """可配置的多层感知机分类器 (与训练时完全一致)。"""

    def __init__(self, input_dim: int, hidden_dims: list,
                 output_dim: int, dropout_rate: float, use_batch_norm: bool):
        super().__init__()
        layers = []
        in_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(in_dim, h_dim))
            if use_batch_norm:
                layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout_rate))
            in_dim = h_dim
        layers.append(nn.Linear(in_dim, output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def load_model(input_dim: int, checkpoint_name: str) -> MLPClassifier:
    """
    加载保存的模型权重。

    Parameters
    ----------
    input_dim : int
        输入特征数 (6 或 16)
    checkpoint_name : str
        模型文件名 (如 'best_model_feat6.pt')

    Returns
    -------
    MLPClassifier (已置于 eval 模式)
    """
    model = MLPClassifier(
        input_dim=input_dim,
        hidden_dims=HIDDEN_DIMS,
        output_dim=1,
        dropout_rate=DROPOUT_RATE,
        use_batch_norm=USE_BATCH_NORM,
    ).to(DEVICE)

    ckpt = torch.load(f"{MODEL_DIR}/{checkpoint_name}",
                      map_location=DEVICE, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model

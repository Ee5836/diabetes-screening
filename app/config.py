"""
全局配置常量
============
"""
import os
import torch

# ---- 路径 ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "output", "nhanes_diabetes_2017_2020_v2.csv")
MODEL_DIR = os.path.join(BASE_DIR, "output", "models")

# ---- 设备 ----
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---- 模型超参 (与训练时一致) ----
HIDDEN_DIMS = [256, 128, 64]
DROPOUT_RATE = 0.3
USE_BATCH_NORM = True

# ---- 特征列定义 ----
FEAT6_COLS = ["RIAGENDR", "RIDAGEYR", "RIDRETH3", "LBDGLUSI", "LBXGH", "BMXBMI"]

FEAT16_COLS = [
    "RIAGENDR", "RIDAGEYR", "RIDRETH3", "LBDGLUSI", "LBXGH", "BMXBMI",
    "HOMA_IR", "EGFR", "URDACT", "BP_SYS_AVG", "BP_DIA_AVG",
    "LBXSTR", "LBXSGTSI", "LBXSUA", "LBXSATSI", "LBXVD3MS",
]

# ---- 种族映射 ----
RACE_MAP = {
    "墨西哥裔美国人": 1,
    "其他西班牙裔": 2,
    "非西班牙裔白人": 3,
    "非西班牙裔黑人": 4,
    "非西班牙裔亚裔": 6,
    "其他/多种族": 7,
}

# ---- 模型 AUC (来自实验评估) ----
AUC_BASELINE = 0.9222
AUC_EXTENDED = 0.9322

# ---- 服务器 ----
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 7861

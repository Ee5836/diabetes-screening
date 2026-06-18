"""
==========================================================================
糖尿病预测 —— 深度学习实验 (v2 — 扩展版)
==========================================================================
基于 NHANES 2017-2020 扩展数据集 (32 列)，使用 PyTorch MLP 进行糖尿病预测。

与 v1 对比:
  - 新增 10 个临床特征 (HOMA-IR, eGFR, 血压, 尿蛋白, 血脂, 肝酶, 维生素D)
  - feat6 实验复现以建立可比基线
  - 新增 feat_extended 实验验证扩展特征的增益
  - feat_all 实验验证所有特征(含问卷)
  - multiclass 使用扩展特征集

输出:
  - 控制台打印全部指标
  - output/figures/ 保存所有图表
  - output/models/  保存最优模型 checkpoint
==========================================================================
"""

import os
import random
import warnings
from typing import Tuple, Dict, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, precision_recall_curve, average_precision_score,
    confusion_matrix, classification_report
)

warnings.filterwarnings("ignore")

# =====================================================================
# 全局配置
# =====================================================================
CONFIG = {
    # ---- 路径 ----
    "data_path":       "./output/nhanes_diabetes_2020_2023_v2.csv",
    "output_figures":  "./output/figures",
    "output_models":   "./output/models",
    "random_seed":     42,

    # ---- 数据预处理 ----
    "min_age":                   8,
    "test_size":                 0.15,
    "val_size":                  0.15,
    "numeric_fill_strategy":    "median",

    # ---- 特征集定义 ----
    # feat6: 基础特征 (与 v1 相同，用于复现对比)
    "feature_set_6": [
        "RIAGENDR", "RIDAGEYR", "RIDRETH3",
        "LBDGLUSI", "LBXGH", "BMXBMI"
    ],

    # feat_extended: 基础 + 新增临床特征 (10个)
    "feature_set_extended": [
        # 基础 6 个
        "RIAGENDR", "RIDAGEYR", "RIDRETH3",
        "LBDGLUSI", "LBXGH", "BMXBMI",
        # 胰岛素抵抗
        "HOMA_IR",
        # 肾脏
        "EGFR", "URDACT",
        # 血压
        "BP_SYS_AVG", "BP_DIA_AVG",
        # 血脂 & 肝酶
        "LBXSTR", "LBXSGTSI", "LBXSUA", "LBXSATSI",
        # 维生素 D
        "LBXVD3MS",
    ],

    # feat_all: 扩展特征 + 问卷
    "feature_set_all": [
        "RIAGENDR", "RIDAGEYR", "RIDRETH3",
        "LBDGLUSI", "LBXGH", "BMXBMI",
        "HOMA_IR", "EGFR", "URDACT",
        "BP_SYS_AVG", "BP_DIA_AVG",
        "LBXSTR", "LBXSGTSI", "LBXSUA", "LBXSATSI", "LBXVD3MS",
        "DIQ010", "DIQ050", "DIQ070",
    ],

    # ---- 模型结构 ----
    "hidden_dims":        [256, 128, 64],
    "dropout_rate":       0.3,
    "use_batch_norm":     True,

    # ---- 训练 ----
    "batch_size":         64,
    "learning_rate":      1e-3,
    "weight_decay":       1e-4,
    "max_epochs":         200,
    "early_stop_patience": 25,
    "lr_patience":        10,
    "lr_factor":          0.5,
    "lr_min":             1e-6,

    # ---- 设备 ----
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "num_workers": 0,
}


# =====================================================================
# 工具函数
# =====================================================================
def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def ensure_dirs() -> None:
    os.makedirs(CONFIG["output_figures"], exist_ok=True)
    os.makedirs(CONFIG["output_models"], exist_ok=True)


# =====================================================================
# PyTorch Dataset
# =====================================================================
class DiabetesDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


# =====================================================================
# 模型定义
# =====================================================================
class MLPClassifier(nn.Module):
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


# =====================================================================
# 数据预处理
# =====================================================================
def preprocess_data(
    df: pd.DataFrame,
    feature_cols: list,
    target_col: str,
    task: str = "binary"
) -> Dict:
    df = df.copy()

    # ---------- 1. 年龄过滤 ----------
    initial_len = len(df)
    df = df[df["RIDAGEYR"] >= CONFIG["min_age"]].copy()
    n_filtered = initial_len - len(df)

    # ---------- 2. 问卷特征特殊处理 (仅当它们在特征列表中时) ----------
    if "DIQ010" in feature_cols and "DIQ010" in df.columns:
        # DIQ010 code=9 (Don't know) 删除
        n_code9 = (df["DIQ010"] == 9).sum()
        if n_code9 > 0:
            df = df[df["DIQ010"] != 9].copy()
        # DIQ010 NaN → 填充 2 (No)
        df["DIQ010"].fillna(2, inplace=True)

    # DIQ050/DIQ070 skip-pattern
    if "DIQ010" in df.columns:
        not_asked = df["DIQ010"] != 1
        for col in ["DIQ050", "DIQ070"]:
            if col in feature_cols and col in df.columns:
                df.loc[not_asked & df[col].isna(), col] = 2

    for col in ["DIQ050", "DIQ070"]:
        if col in feature_cols and col in df.columns and df[col].isna().any():
            mode_val = df[col].mode().iloc[0] if not df[col].mode().empty else 2
            df[col].fillna(mode_val, inplace=True)

    # DIQ010 映射: 1→1, 2→0, 3→0.5
    if "DIQ010" in feature_cols and "DIQ010" in df.columns:
        diq010_map = {1: 1, 2: 0, 3: 0.5}
        df["DIQ010"] = df["DIQ010"].map(diq010_map)

    # DIQ050/DIQ070: 1→1, 2→0
    for col in ["DIQ050", "DIQ070"]:
        if col in feature_cols and col in df.columns:
            df[col] = df[col].map({1: 1, 2: 0})

    # ---------- 3. RIAGENDR: 1→0(M), 2→1(F) ----------
    if "RIAGENDR" in feature_cols and "RIAGENDR" in df.columns:
        df["RIAGENDR"] = df["RIAGENDR"].map({1: 0, 2: 1})

    # ---------- 4. 目标变量 ----------
    if task == "multiclass":
        le = LabelEncoder()
        y_all = le.fit_transform(df[target_col])
    else:
        le = None
        y_all = df[target_col].values.astype(np.float32)

    # ---------- 5. 特征矩阵 ----------
    available_features = [c for c in feature_cols if c in df.columns]
    missing_features = set(feature_cols) - set(available_features)
    if missing_features:
        print(f"  警告: 以下特征在数据中不存在: {missing_features}")
    X_all = df[available_features].copy()

    # ---------- 6. 分层分割 ----------
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X_all, y_all, test_size=CONFIG["test_size"],
        stratify=y_all, random_state=CONFIG["random_seed"]
    )
    val_frac = CONFIG["val_size"] / (1 - CONFIG["test_size"])
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=val_frac,
        stratify=y_trainval, random_state=CONFIG["random_seed"]
    )

    print(f"  年龄过滤: {initial_len} -> {len(df)} (-{n_filtered})")
    print(f"  分割: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    # ---------- 7. 缺失值填补 ----------
    imp = SimpleImputer(strategy=CONFIG["numeric_fill_strategy"])
    X_train = imp.fit_transform(X_train)
    X_val = imp.transform(X_val)
    X_test = imp.transform(X_test)

    assert not np.isnan(X_train).any()
    assert not np.isnan(X_val).any()
    assert not np.isnan(X_test).any()

    # ---------- 8. 标准化 ----------
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)

    # ---------- 9. 类别权重 ----------
    result = {
        "X_train": X_train.astype(np.float32),
        "X_val":   X_val.astype(np.float32),
        "X_test":  X_test.astype(np.float32),
        "y_train": y_train,
        "y_val":   y_val,
        "y_test":  y_test,
        "scaler":  scaler,
        "label_encoder": le,
        "feature_names": available_features,
    }

    if task == "binary":
        n_pos = (y_train == 1).sum()
        n_neg = (y_train == 0).sum()
        pos_weight = n_neg / n_pos if n_pos > 0 else 1.0
        result["pos_weight"] = pos_weight
        print(f"  pos_weight (neg/pos): {pos_weight:.2f}")
    else:
        classes, counts = np.unique(y_train, return_counts=True)
        class_w = len(y_train) / (len(classes) * counts)
        result["class_weights"] = torch.tensor(class_w, dtype=torch.float32)
        print(f"  class_weights: {class_w}")

    return result


# =====================================================================
# 指标计算
# =====================================================================
def compute_metrics(y_true, y_pred_probs, task="binary") -> dict:
    metrics = {}
    if task == "binary":
        y_pred = (y_pred_probs >= 0.5).astype(int)
        metrics["accuracy"] = accuracy_score(y_true, y_pred)
        metrics["precision"] = precision_score(y_true, y_pred, zero_division=0)
        metrics["recall"] = recall_score(y_true, y_pred, zero_division=0)
        metrics["f1"] = f1_score(y_true, y_pred, zero_division=0)
        try:
            metrics["auc"] = roc_auc_score(y_true, y_pred_probs)
        except ValueError:
            metrics["auc"] = 0.5
    else:
        y_pred = np.argmax(y_pred_probs, axis=1)
        metrics["accuracy"] = accuracy_score(y_true, y_pred)
        metrics["precision"] = precision_score(y_true, y_pred, average="macro", zero_division=0)
        metrics["recall"] = recall_score(y_true, y_pred, average="macro", zero_division=0)
        metrics["f1"] = f1_score(y_true, y_pred, average="macro", zero_division=0)
        try:
            metrics["auc"] = roc_auc_score(y_true, y_pred_probs, multi_class="ovr")
        except ValueError:
            metrics["auc"] = 0.5
    return metrics


# =====================================================================
# 训练函数
# =====================================================================
def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: dict,
    task: str = "binary",
    pos_weight: Optional[float] = None,
    class_weights: Optional[torch.Tensor] = None,
    save_path: Optional[str] = None,
) -> Tuple[nn.Module, dict, float]:
    device = torch.device(config["device"])
    model = model.to(device)

    if task == "binary":
        pw = torch.tensor([pos_weight], device=device) if pos_weight else None
        criterion = nn.BCEWithLogitsLoss(pos_weight=pw)
    else:
        cw = class_weights.to(device) if class_weights is not None else None
        criterion = nn.CrossEntropyLoss(weight=cw)

    optimizer = optim.Adam(model.parameters(), lr=config["learning_rate"],
                           weight_decay=config["weight_decay"])
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=config["lr_factor"],
        patience=config["lr_patience"], min_lr=config["lr_min"]
    )

    best_val_loss = float("inf")
    best_model_state = None
    patience_counter = 0
    history = {"train_loss": [], "val_loss": [], "train_auc": [], "val_auc": []}

    for epoch in range(config["max_epochs"]):
        # ---- Train ----
        model.train()
        train_loss = 0.0
        train_probs, train_labels = [], []

        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            logits = model(X_batch)
            if task == "binary":
                logits = logits.squeeze(-1)
            loss = criterion(logits, y_batch if task == "binary" else y_batch.long())
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * X_batch.size(0)
            with torch.no_grad():
                if task == "binary":
                    train_probs.append(torch.sigmoid(logits).cpu().numpy())
                else:
                    train_probs.append(torch.softmax(logits, dim=1).cpu().numpy())
            train_labels.append(y_batch.cpu().numpy())

        train_loss /= len(train_loader.dataset)
        train_probs = np.concatenate(train_probs)
        train_labels = np.concatenate(train_labels)

        # ---- Val ----
        model.eval()
        val_loss = 0.0
        val_probs, val_labels = [], []

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                logits = model(X_batch)
                if task == "binary":
                    logits = logits.squeeze(-1)
                loss = criterion(logits, y_batch if task == "binary" else y_batch.long())

                val_loss += loss.item() * X_batch.size(0)
                if task == "binary":
                    val_probs.append(torch.sigmoid(logits).cpu().numpy())
                else:
                    val_probs.append(torch.softmax(logits, dim=1).cpu().numpy())
                val_labels.append(y_batch.cpu().numpy())

        val_loss /= len(val_loader.dataset)
        val_probs = np.concatenate(val_probs)
        val_labels = np.concatenate(val_labels)

        train_auc = _safe_auc(train_labels, train_probs, task)
        val_auc = _safe_auc(val_labels, val_probs, task)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_auc"].append(train_auc)
        history["val_auc"].append(val_auc)

        scheduler.step(val_loss)
        current_lr = optimizer.param_groups[0]["lr"]

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:3d} | "
                  f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} | "
                  f"train_auc={train_auc:.4f} val_auc={val_auc:.4f} | "
                  f"lr={current_lr:.2e} | patience={patience_counter}")

        if patience_counter >= config["early_stop_patience"]:
            print(f"  >>> 早停于 epoch {epoch+1}")
            break

    model.load_state_dict(best_model_state)

    if save_path:
        torch.save({
            "model_state_dict": best_model_state,
            "config": {k: v for k, v in config.items() if k != "device"},
            "best_val_loss": best_val_loss,
            "history": history,
        }, save_path)
        print(f"  模型已保存至: {save_path}")

    return model, history, best_val_loss


def _safe_auc(y_true, y_pred_probs, task="binary") -> float:
    try:
        if task == "binary":
            if len(np.unique(y_true)) < 2:
                return 0.5
            return roc_auc_score(y_true, y_pred_probs)
        else:
            return roc_auc_score(y_true, y_pred_probs, multi_class="ovr")
    except ValueError:
        return 0.5


# =====================================================================
# 评估与可视化
# =====================================================================
def evaluate_model(
    model: nn.Module,
    test_loader: DataLoader,
    history: dict,
    label_encoder,
    task: str = "binary",
    feature_set_name: str = "feat6",
) -> dict:
    device = torch.device(CONFIG["device"])
    model = model.to(device)
    model.eval()

    test_probs, test_labels = [], []
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(device)
            logits = model(X_batch)
            if task == "binary":
                logits = logits.squeeze(-1)
                probs = torch.sigmoid(logits).cpu().numpy()
            else:
                probs = torch.softmax(logits, dim=1).cpu().numpy()
            test_probs.append(probs)
            test_labels.append(y_batch.cpu().numpy())

    test_probs = np.concatenate(test_probs)
    test_labels = np.concatenate(test_labels)

    class_names = (list(label_encoder.classes_) if (task == "multiclass" and label_encoder)
                   else ["非糖尿病", "糖尿病"])

    # ---- 打印指标 ----
    print(f"\n{'='*60}")
    print(f"  测试集评估: {feature_set_name} ({task})")
    print(f"{'='*60}")

    if task == "binary":
        metrics = compute_metrics(test_labels, test_probs, task="binary")
        print(f"  Accuracy :  {metrics['accuracy']:.4f}")
        print(f"  Precision:  {metrics['precision']:.4f}")
        print(f"  Recall   :  {metrics['recall']:.4f}")
        print(f"  F1-score :  {metrics['f1']:.4f}")
        print(f"  AUC-ROC  :  {metrics['auc']:.4f}")

        fpr, tpr, thresholds = roc_curve(test_labels, test_probs)
        youden = tpr - fpr
        best_thresh = thresholds[np.argmax(youden)]
        y_pred_opt = (test_probs >= best_thresh).astype(int)
        print(f"\n  --- 最优阈值 (Youden) ---")
        print(f"  阈值 = {best_thresh:.4f}")
        print(f"  Accuracy :  {accuracy_score(test_labels, y_pred_opt):.4f}")
        print(f"  Precision:  {precision_score(test_labels, y_pred_opt, zero_division=0):.4f}")
        print(f"  Recall   :  {recall_score(test_labels, y_pred_opt, zero_division=0):.4f}")
        print(f"  F1-score :  {f1_score(test_labels, y_pred_opt, zero_division=0):.4f}")
    else:
        y_pred = np.argmax(test_probs, axis=1)
        metrics = compute_metrics(test_labels, test_probs, task="multiclass")
        print(f"  Accuracy (macro):  {metrics['accuracy']:.4f}")
        print(f"  Precision (macro): {metrics['precision']:.4f}")
        print(f"  Recall    (macro): {metrics['recall']:.4f}")
        print(f"  F1-score  (macro): {metrics['f1']:.4f}")
        print(f"  AUC-ROC   (ovr) : {metrics['auc']:.4f}")
        print(f"\n--- 分类报告 ---")
        print(classification_report(test_labels, y_pred, target_names=class_names, zero_division=0))

    # ---- 绘图 ----
    fig_dir = CONFIG["output_figures"]
    prefix = f"{fig_dir}/{feature_set_name}"

    _plot_training_curves(history, f"{prefix}_training_curves.png")

    if task == "binary":
        _plot_roc_curve(test_labels, test_probs, f"{prefix}_roc_curve.png")
        _plot_pr_curve(test_labels, test_probs, f"{prefix}_pr_curve.png")
        y_pred = (test_probs >= 0.5).astype(int)
        _plot_confusion_matrix(test_labels, y_pred, class_names,
                               f"{prefix}_confusion_matrix.png")
    else:
        y_pred = np.argmax(test_probs, axis=1)
        _plot_confusion_matrix(test_labels, y_pred, class_names,
                               f"{prefix}_confusion_matrix.png")

    plt.close("all")
    return metrics


def _plot_training_curves(history: dict, save_path: str) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    epochs = range(1, len(history["train_loss"]) + 1)
    best_epoch = np.argmin(history["val_loss"]) + 1

    ax1.plot(epochs, history["train_loss"], label="Train Loss", linewidth=1.5)
    ax1.plot(epochs, history["val_loss"], label="Val Loss", linewidth=1.5)
    ax1.axvline(best_epoch, color="gray", linestyle="--", alpha=0.7, label=f"Best epoch={best_epoch}")
    ax1.set_xlabel("Epoch"); ax1.set_ylabel("Loss")
    ax1.set_title("Training & Validation Loss")
    ax1.legend(); ax1.grid(True, alpha=0.3)

    ax2.plot(epochs, history["train_auc"], label="Train AUC", linewidth=1.5)
    ax2.plot(epochs, history["val_auc"], label="Val AUC", linewidth=1.5)
    ax2.axvline(best_epoch, color="gray", linestyle="--", alpha=0.7, label=f"Best epoch={best_epoch}")
    ax2.set_xlabel("Epoch"); ax2.set_ylabel("AUC-ROC")
    ax2.set_title("Training & Validation AUC")
    ax2.legend(); ax2.grid(True, alpha=0.3)

    plt.tight_layout(); plt.savefig(save_path, dpi=150, bbox_inches="tight"); plt.close()


def _plot_roc_curve(y_true, y_probs, save_path: str) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_probs)
    auc = roc_auc_score(y_true, y_probs)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, linewidth=2, label=f"AUC = {auc:.4f}")
    plt.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random")
    plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
    plt.title("ROC Curve"); plt.legend(loc="lower right"); plt.grid(True, alpha=0.3)
    plt.tight_layout(); plt.savefig(save_path, dpi=150, bbox_inches="tight"); plt.close()


def _plot_pr_curve(y_true, y_probs, save_path: str) -> None:
    precision, recall, _ = precision_recall_curve(y_true, y_probs)
    ap = average_precision_score(y_true, y_probs)
    baseline = y_true.mean()
    plt.figure(figsize=(6, 5))
    plt.plot(recall, precision, linewidth=2, label=f"AP = {ap:.4f}")
    plt.axhline(baseline, color="gray", linestyle="--", alpha=0.5, label=f"No-skill ({baseline:.3f})")
    plt.xlabel("Recall"); plt.ylabel("Precision")
    plt.title("Precision-Recall Curve"); plt.legend(loc="upper right"); plt.grid(True, alpha=0.3)
    plt.tight_layout(); plt.savefig(save_path, dpi=150, bbox_inches="tight"); plt.close()


def _plot_confusion_matrix(y_true, y_pred, class_names, save_path: str) -> None:
    cm = confusion_matrix(y_true, y_pred)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=class_names, yticklabels=class_names, ax=ax1)
    ax1.set_xlabel("Predicted"); ax1.set_ylabel("True"); ax1.set_title("Confusion Matrix (Count)")
    sns.heatmap(cm_norm, annot=True, fmt=".1%", cmap="Blues", xticklabels=class_names, yticklabels=class_names, ax=ax2)
    ax2.set_xlabel("Predicted"); ax2.set_ylabel("True"); ax2.set_title("Confusion Matrix (Normalized)")
    plt.tight_layout(); plt.savefig(save_path, dpi=150, bbox_inches="tight"); plt.close()


# =====================================================================
# 结果汇总
# =====================================================================
def print_summary(all_results: list) -> None:
    """打印并绘制所有实验的汇总对比，包含与 v1 的对比。"""
    print(f"\n{'='*75}")
    print(f"  实验汇总对比 (v2 扩展版)")
    print(f"{'='*75}")

    # 当前实验
    results = all_results[-1] if isinstance(all_results[-1], dict) else {}
    # 构建表格
    rows = []
    for entry in all_results:
        for name, m in entry.items():
            rows.append((name, m))

    print(f"  {'Experiment':<30} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8} {'AUC':>8}")
    print(f"  {'-'*62}")
    for name, m in rows:
        print(f"  {name:<30} {m['accuracy']:>8.4f} {m['precision']:>8.4f} "
              f"{m['recall']:>8.4f} {m['f1']:>8.4f} {m['auc']:>8.4f}")

    # ---- 汇总柱状图 ----
    names = [r[0] for r in rows]
    metrics_list = ["accuracy", "precision", "recall", "f1", "auc"]
    x = np.arange(len(names))
    width = 0.15
    colors = ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6"]

    fig, ax = plt.subplots(figsize=(14, 6))
    for i, (metric, color) in enumerate(zip(metrics_list, colors)):
        values = [r[1][metric] for r in rows]
        bars = ax.bar(x + i * width, values, width, label=metric.upper(), color=color, alpha=0.85)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=6.5, rotation=90)

    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(names, fontsize=7, rotation=15, ha="right")
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score")
    ax.set_title("Experiment Comparison Summary (v2)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.2, axis="y")
    plt.tight_layout()
    save_path = f"{CONFIG['output_figures']}/comparison_summary.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  汇总图已保存至: {save_path}")


# =====================================================================
# 主函数
# =====================================================================
def main() -> None:
    print("=" * 60)
    print("  糖尿病预测 —— 深度学习实验 (v2 扩展版)")
    print(f"  设备: {CONFIG['device']}")
    print("=" * 60)

    set_seed(CONFIG["random_seed"])
    ensure_dirs()

    # ---- 加载数据 ----
    print(f"\n[0] 加载数据: {CONFIG['data_path']}")
    df = pd.read_csv(CONFIG["data_path"])
    print(f"  原始数据: {df.shape[0]} 行 × {df.shape[1]} 列")
    print(f"  新增临床特征: HOMA_IR, EGFR, BP_SYS_AVG, BP_DIA_AVG, "
          f"URDACT, LBXSTR, LBXSGTSI, LBXSUA, LBXSATSI, LBXVD3MS")

    all_results = []

    # ==================================================================
    # 实验 1: feat6 (baseline, 复现 v1)
    # ==================================================================
    print(f"\n{'='*60}")
    print(f"  实验 1/4: feat6 (baseline 复现) → DIABETES_GROUP")
    print(f"{'='*60}")

    prep1 = preprocess_data(df, CONFIG["feature_set_6"],
                            target_col="DIABETES_GROUP", task="binary")

    train_ds1 = DiabetesDataset(prep1["X_train"], prep1["y_train"])
    val_ds1 = DiabetesDataset(prep1["X_val"], prep1["y_val"])
    test_ds1 = DiabetesDataset(prep1["X_test"], prep1["y_test"])

    model1 = MLPClassifier(input_dim=prep1["X_train"].shape[1],
                           hidden_dims=CONFIG["hidden_dims"], output_dim=1,
                           dropout_rate=CONFIG["dropout_rate"],
                           use_batch_norm=CONFIG["use_batch_norm"])
    print(f"  特征数: {prep1['X_train'].shape[1]}, 参数量: {sum(p.numel() for p in model1.parameters()):,}")

    train_loader1 = DataLoader(train_ds1, batch_size=CONFIG["batch_size"], shuffle=True,
                               num_workers=CONFIG["num_workers"])
    val_loader1 = DataLoader(val_ds1, batch_size=CONFIG["batch_size"], shuffle=False,
                             num_workers=CONFIG["num_workers"])
    test_loader1 = DataLoader(test_ds1, batch_size=CONFIG["batch_size"], shuffle=False,
                              num_workers=CONFIG["num_workers"])

    model1, history1, _ = train_model(
        model1, train_loader1, val_loader1, CONFIG,
        task="binary", pos_weight=prep1["pos_weight"],
        save_path=f"{CONFIG['output_models']}/best_model_feat6.pt")

    m1 = evaluate_model(model1, test_loader1, history1, None,
                        task="binary", feature_set_name="feat6_baseline")
    all_results.append({"feat6 (baseline 6feat)": m1})

    # ==================================================================
    # 实验 2: feat_extended (新增临床特征)
    # ==================================================================
    print(f"\n{'='*60}")
    print(f"  实验 2/4: feat_extended (16个临床特征) → DIABETES_GROUP")
    print(f"{'='*60}")

    prep2 = preprocess_data(df, CONFIG["feature_set_extended"],
                            target_col="DIABETES_GROUP", task="binary")

    train_ds2 = DiabetesDataset(prep2["X_train"], prep2["y_train"])
    val_ds2 = DiabetesDataset(prep2["X_val"], prep2["y_val"])
    test_ds2 = DiabetesDataset(prep2["X_test"], prep2["y_test"])

    model2 = MLPClassifier(input_dim=prep2["X_train"].shape[1],
                           hidden_dims=CONFIG["hidden_dims"], output_dim=1,
                           dropout_rate=CONFIG["dropout_rate"],
                           use_batch_norm=CONFIG["use_batch_norm"])
    print(f"  特征数: {prep2['X_train'].shape[1]}, 参数量: {sum(p.numel() for p in model2.parameters()):,}")

    train_loader2 = DataLoader(train_ds2, batch_size=CONFIG["batch_size"], shuffle=True,
                               num_workers=CONFIG["num_workers"])
    val_loader2 = DataLoader(val_ds2, batch_size=CONFIG["batch_size"], shuffle=False,
                             num_workers=CONFIG["num_workers"])
    test_loader2 = DataLoader(test_ds2, batch_size=CONFIG["batch_size"], shuffle=False,
                              num_workers=CONFIG["num_workers"])

    model2, history2, _ = train_model(
        model2, train_loader2, val_loader2, CONFIG,
        task="binary", pos_weight=prep2["pos_weight"],
        save_path=f"{CONFIG['output_models']}/best_model_feat_extended.pt")

    m2 = evaluate_model(model2, test_loader2, history2, None,
                        task="binary", feature_set_name="feat_extended")
    all_results.append({"feat_extended (16feat)": m2})

    # ==================================================================
    # 实验 3: feat_all (扩展 + 问卷)
    # ==================================================================
    print(f"\n{'='*60}")
    print(f"  实验 3/4: feat_all (全部特征含问卷) → DIABETES_GROUP")
    print(f"{'='*60}")

    prep3 = preprocess_data(df, CONFIG["feature_set_all"],
                            target_col="DIABETES_GROUP", task="binary")

    train_ds3 = DiabetesDataset(prep3["X_train"], prep3["y_train"])
    val_ds3 = DiabetesDataset(prep3["X_val"], prep3["y_val"])
    test_ds3 = DiabetesDataset(prep3["X_test"], prep3["y_test"])

    model3 = MLPClassifier(input_dim=prep3["X_train"].shape[1],
                           hidden_dims=CONFIG["hidden_dims"], output_dim=1,
                           dropout_rate=CONFIG["dropout_rate"],
                           use_batch_norm=CONFIG["use_batch_norm"])
    print(f"  特征数: {prep3['X_train'].shape[1]}, 参数量: {sum(p.numel() for p in model3.parameters()):,}")

    train_loader3 = DataLoader(train_ds3, batch_size=CONFIG["batch_size"], shuffle=True,
                               num_workers=CONFIG["num_workers"])
    val_loader3 = DataLoader(val_ds3, batch_size=CONFIG["batch_size"], shuffle=False,
                             num_workers=CONFIG["num_workers"])
    test_loader3 = DataLoader(test_ds3, batch_size=CONFIG["batch_size"], shuffle=False,
                              num_workers=CONFIG["num_workers"])

    model3, history3, _ = train_model(
        model3, train_loader3, val_loader3, CONFIG,
        task="binary", pos_weight=prep3["pos_weight"],
        save_path=f"{CONFIG['output_models']}/best_model_feat_all.pt")

    m3 = evaluate_model(model3, test_loader3, history3, None,
                        task="binary", feature_set_name="feat_all")
    all_results.append({"feat_all (含问卷)": m3})

    # ==================================================================
    # 实验 4: multiclass (扩展特征 → 四分类)
    # ==================================================================
    print(f"\n{'='*60}")
    print(f"  实验 4/4: multiclass (扩展特征) → DIABETES_STATUS")
    print(f"{'='*60}")

    prep4 = preprocess_data(df, CONFIG["feature_set_extended"],
                            target_col="DIABETES_STATUS", task="multiclass")

    train_ds4 = DiabetesDataset(prep4["X_train"], prep4["y_train"])
    val_ds4 = DiabetesDataset(prep4["X_val"], prep4["y_val"])
    test_ds4 = DiabetesDataset(prep4["X_test"], prep4["y_test"])

    n_classes = len(np.unique(prep4["y_train"]))
    model4 = MLPClassifier(input_dim=prep4["X_train"].shape[1],
                           hidden_dims=CONFIG["hidden_dims"], output_dim=n_classes,
                           dropout_rate=CONFIG["dropout_rate"],
                           use_batch_norm=CONFIG["use_batch_norm"])
    print(f"  特征数: {prep4['X_train'].shape[1]}, 类别数: {n_classes}, "
          f"参数量: {sum(p.numel() for p in model4.parameters()):,}")

    train_loader4 = DataLoader(train_ds4, batch_size=CONFIG["batch_size"], shuffle=True,
                               num_workers=CONFIG["num_workers"])
    val_loader4 = DataLoader(val_ds4, batch_size=CONFIG["batch_size"], shuffle=False,
                             num_workers=CONFIG["num_workers"])
    test_loader4 = DataLoader(test_ds4, batch_size=CONFIG["batch_size"], shuffle=False,
                              num_workers=CONFIG["num_workers"])

    model4, history4, _ = train_model(
        model4, train_loader4, val_loader4, CONFIG,
        task="multiclass", class_weights=prep4["class_weights"],
        save_path=f"{CONFIG['output_models']}/best_model_multiclass.pt")

    m4 = evaluate_model(model4, test_loader4, history4, prep4["label_encoder"],
                        task="multiclass", feature_set_name="multiclass_extended")
    all_results.append({"multiclass (16feat→4类)": m4})

    # ==================================================================
    # 汇总
    # ==================================================================
    print_summary(all_results)
    print(f"\n{'='*60}")
    print(f"  实验完成！")
    print(f"  图表目录: {os.path.abspath(CONFIG['output_figures'])}")
    print(f"  模型目录: {os.path.abspath(CONFIG['output_models'])}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

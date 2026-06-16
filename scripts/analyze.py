"""
==========================================================================
项目结果综合分析 —— 可视化脚本
==========================================================================
生成: 特征重要性排名图、v1/v2对比雷达图、增益分析图
==========================================================================
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FIG_DIR = "./output/figures"

# ============================================================
# 图1: 特征重要性综合排名 (Permutation Importance)
# ============================================================
features = [
    "HbA1c (LBXGH)", "Age (RIDAGEYR)", "FPG (LBDGLUSI)", "BMI (BMXBMI)",
    "eGFR", "BP Diastolic", "Vitamin D3", "BP Systolic",
    "Uric Acid", "Triglycerides", "Gender", "AST (GGT)",
    "HOMA-IR", "ALT", "Race", "Urine Alb/Cr"
]
perm_imp = [
    0.131875, 0.062613, 0.030544, 0.023410,
    0.012568, 0.011211, 0.006223, 0.006029,
    0.004582, 0.004548, 0.002038, 0.001499,
    0.001190, 0.001057, 0.000724, 0.000473
]
univar_auc = [
    0.8482, 0.7798, 0.7383, 0.6781,
    0.3778, 0.5297, 0.5230, 0.6502,
    0.5261, 0.6301, 0.4970, 0.6353,
    0.6552, 0.5382, 0.5005, 0.6857
]

# 按 Permutation Importance 排序
sorted_idx = np.argsort(perm_imp)[::-1]
features_sorted = [features[i] for i in sorted_idx]
perm_imp_sorted = [perm_imp[i] for i in sorted_idx]
univar_auc_sorted = [univar_auc[i] for i in sorted_idx]

# 颜色标记: 基础6特征 vs 新增10特征
base6 = {"HbA1c (LBXGH)", "Age (RIDAGEYR)", "FPG (LBDGLUSI)", "BMI (BMXBMI)", "Gender", "Race"}
colors = ["#e74c3c" if f in base6 else "#3498db" for f in features_sorted]

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(range(len(features_sorted)), perm_imp_sorted, color=colors, alpha=0.85, height=0.7)

# 标注数值
for i, (v, u) in enumerate(zip(perm_imp_sorted, univar_auc_sorted)):
    ax.text(v + 0.001, i, f"ΔAUC={v:.4f}  (univar AUC={u:.3f})",
            va="center", fontsize=8, color="gray")

ax.set_yticks(range(len(features_sorted)))
ax.set_yticklabels(features_sorted)
ax.set_xlabel("Permutation Importance (AUC drop)")
ax.set_title("Feature Importance Ranking — feat_extended Model\n(Red = Baseline 6, Blue = New 10)", fontsize=13, fontweight="bold")
ax.invert_yaxis()
ax.grid(True, alpha=0.2, axis="x")

# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor="#e74c3c", label="Baseline 6 features"),
                   Patch(facecolor="#3498db", label="New clinical features")]
ax.legend(handles=legend_elements, loc="lower right")
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/feature_importance_ranking.png", dpi=150, bbox_inches="tight")
plt.close()

# ============================================================
# 图2: v1 vs v2 模型性能对比
# ============================================================
experiments = ["feat6 (v1)", "feat6 (v2 baseline)", "feat_extended (v2)", "feat_all (v2)"]
metrics_data = {
    "Accuracy":  [0.8561, 0.8614, 0.8225, 0.9857],
    "Precision": [0.4812, 0.4921, 0.4235, 0.9119],
    "Recall":    [0.7943, 0.7464, 0.8612, 0.9904],
    "F1-score":  [0.5993, 0.5932, 0.5678, 0.9495],
    "AUC-ROC":   [0.9292, 0.9222, 0.9322, 0.9996],
}

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(experiments))
width = 0.15
colors_m = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]

for i, (metric_name, values) in enumerate(metrics_data.items()):
    bars = ax.bar(x + i * width, values, width, label=metric_name, color=colors_m[i], alpha=0.85)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{val:.3f}", ha="center", va="bottom", fontsize=7, rotation=90)

ax.set_xticks(x + width * 2)
ax.set_xticklabels(experiments, fontsize=10)
ax.set_ylim(0, 1.15)
ax.set_ylabel("Score")
ax.set_title("Model Performance Comparison: v1 vs v2", fontsize=13, fontweight="bold")
ax.legend(loc="lower right", fontsize=8, ncol=3)
ax.grid(True, alpha=0.2, axis="y")
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/v1_v2_comparison.png", dpi=150, bbox_inches="tight")
plt.close()

# ============================================================
# 图3: 扩展模型增益分析 — 被挽救患者特征
# ============================================================
categories = ["Correctly\nby feat6", "RESCUED by\nextended", "Missed by\nboth models"]
counts = [156, 28, 25]
pct = [74.6, 13.4, 12.0]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 饼图
colors_pie = ["#2ecc71", "#3498db", "#e74c3c"]
explode = (0, 0.08, 0)
ax1.pie(counts, explode=explode, labels=categories, colors=colors_pie,
        autopct="%1.1f%%", startangle=90, textprops={"fontsize": 10})
ax1.set_title(f"Diabetic Patient Detection (n={sum(counts)})\nNet Recall Gain: +24 patients", fontsize=12, fontweight="bold")

# 被挽救 vs 被遗漏患者的临床特征对比
rescued_vals = [67.1, 6.18, 5.78, 31.2, 77.8, 132.1]
missed_vals =  [54.1, 5.23, 5.56, 37.9, 78.1, 131.1]
labels_radar = ["Age", "FPG\n(mmol/L)", "HbA1c\n(%)", "BMI", "eGFR", "BP Sys\n(mmHg)"]

# 归一化到 0-1 用于雷达图可视化对比
max_vals = [80, 10, 10, 40, 120, 140]
rescued_norm = [v/m for v, m in zip(rescued_vals, max_vals)]
missed_norm = [v/m for v, m in zip(missed_vals, max_vals)]

N = len(labels_radar)
angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
rescued_norm += rescued_norm[:1]
missed_norm += missed_norm[:1]
angles += angles[:1]

ax2 = fig.add_subplot(122, polar=True)
ax2.fill(angles, rescued_norm, alpha=0.3, color="#3498db", label="Rescued (n=28)")
ax2.plot(angles, rescued_norm, "o-", color="#3498db", linewidth=2)
ax2.fill(angles, missed_norm, alpha=0.3, color="#e74c3c", label="Still Missed (n=25)")
ax2.plot(angles, missed_norm, "o-", color="#e74c3c", linewidth=2)
ax2.set_xticks(angles[:-1])
ax2.set_xticklabels(labels_radar, fontsize=8)
ax2.set_title("Clinical Profile: Rescued vs Missed", fontsize=12, fontweight="bold", pad=20)
ax2.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/gain_analysis.png", dpi=150, bbox_inches="tight")
plt.close()

# ============================================================
# 图4: 多分类混淆模式
# ============================================================
cm_pct = np.array([
    [52.2, 26.1, 4.4, 17.2],
    [24.1, 72.4, 0.0, 3.4],
    [14.0, 0.0, 78.6, 7.4],
    [3.2, 7.3, 6.3, 83.2],
])
classes = ["Diagnosed\nDiabetes", "Undiagnosed\nDiabetes", "Normal", "Prediabetic"]

fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(cm_pct, cmap="YlOrRd", vmin=0, vmax=100)

for i in range(4):
    for j in range(4):
        color = "white" if cm_pct[i, j] > 50 else "black"
        ax.text(j, i, f"{cm_pct[i, j]:.1f}%", ha="center", va="center",
                fontsize=13, fontweight="bold", color=color)

ax.set_xticks(range(4)); ax.set_yticks(range(4))
ax.set_xticklabels(classes, fontsize=9)
ax.set_yticklabels(classes, fontsize=9)
ax.set_xlabel("Predicted", fontsize=11)
ax.set_ylabel("True", fontsize=11)
ax.set_title("Multiclass Confusion Matrix (%)\nfeat_extended → 4-class", fontsize=13, fontweight="bold")
plt.colorbar(im, ax=ax, label="% of True Class")
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/multiclass_confusion_pct.png", dpi=150, bbox_inches="tight")
plt.close()

print("Analysis visualizations generated:")
print(f"  1. {FIG_DIR}/feature_importance_ranking.png")
print(f"  2. {FIG_DIR}/v1_v2_comparison.png")
print(f"  3. {FIG_DIR}/gain_analysis.png")
print(f"  4. {FIG_DIR}/multiclass_confusion_pct.png")

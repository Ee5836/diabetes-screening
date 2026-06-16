"""
推理逻辑
========
预测函数 + 结果格式化。
"""
import numpy as np
import torch

from .config import DEVICE, FEAT6_COLS, FEAT16_COLS, RACE_MAP


def _predict_basic_core(prep, model,
                        age, gender, race, hba1c, fasting_glucose, bmi) -> float:
    """基础 6 特征预测 → 原始概率值 (0~1)。"""
    race_code = RACE_MAP.get(race, 3)
    gender_code = _encode_gender(gender)

    raw = {
        "RIAGENDR": gender_code, "RIDAGEYR": age, "RIDRETH3": race_code,
        "LBDGLUSI": fasting_glucose, "LBXGH": hba1c, "BMXBMI": bmi,
    }
    features = prep.fill_missing(raw)
    features_scaled = prep.transform(features)
    return _infer(model, features_scaled)


def predict_basic(prep, model, best_thresh: float, auc: float,
                  age, gender, race, hba1c, fasting_glucose, bmi) -> str:
    """基础 6 特征预测 → HTML 结果。"""
    prob = _predict_basic_core(prep, model, age, gender, race,
                               hba1c, fasting_glucose, bmi)
    return _format_result(prob, best_thresh, auc)


def predict_basic_json(prep, model, best_thresh: float, auc: float,
                       age, gender, race, hba1c, fasting_glucose, bmi) -> dict:
    """基础 6 特征预测 → JSON 结构化结果。"""
    prob = _predict_basic_core(prep, model, age, gender, race,
                               hba1c, fasting_glucose, bmi)
    return _format_result_json(prob, best_thresh, auc)


def _predict_advanced_core(prep, model,
                           age, gender, race, hba1c, fasting_glucose, bmi,
                           homa_ir, egfr, urdact, bp_sys, bp_dia,
                           triglyc, ggt, uric_acid, alt, vit_d3) -> float:
    """全部 16 特征预测 → 原始概率值 (0~1)。"""
    race_code = RACE_MAP.get(race, 3)
    gender_code = _encode_gender(gender)

    raw = {
        "RIAGENDR": gender_code, "RIDAGEYR": age, "RIDRETH3": race_code,
        "LBDGLUSI": fasting_glucose, "LBXGH": hba1c, "BMXBMI": bmi,
        "HOMA_IR": homa_ir, "EGFR": egfr, "URDACT": urdact,
        "BP_SYS_AVG": bp_sys, "BP_DIA_AVG": bp_dia,
        "LBXSTR": triglyc, "LBXSGTSI": ggt, "LBXSUA": uric_acid,
        "LBXSATSI": alt, "LBXVD3MS": vit_d3,
    }
    features = prep.fill_missing(raw)
    features_scaled = prep.transform(features)
    return _infer(model, features_scaled)


def predict_advanced(prep, model, best_thresh: float, auc: float,
                     age, gender, race, hba1c, fasting_glucose, bmi,
                     homa_ir, egfr, urdact, bp_sys, bp_dia,
                     triglyc, ggt, uric_acid, alt, vit_d3) -> str:
    """全部 16 特征预测 → HTML 结果。"""
    prob = _predict_advanced_core(prep, model, age, gender, race,
                                  hba1c, fasting_glucose, bmi,
                                  homa_ir, egfr, urdact, bp_sys, bp_dia,
                                  triglyc, ggt, uric_acid, alt, vit_d3)
    return _format_result(prob, best_thresh, auc)


def predict_advanced_json(prep, model, best_thresh: float, auc: float,
                          age, gender, race, hba1c, fasting_glucose, bmi,
                          homa_ir, egfr, urdact, bp_sys, bp_dia,
                          triglyc, ggt, uric_acid, alt, vit_d3) -> dict:
    """全部 16 特征预测 → JSON 结构化结果。"""
    prob = _predict_advanced_core(prep, model, age, gender, race,
                                  hba1c, fasting_glucose, bmi,
                                  homa_ir, egfr, urdact, bp_sys, bp_dia,
                                  triglyc, ggt, uric_acid, alt, vit_d3)
    return _format_result_json(prob, best_thresh, auc)


def compute_optimal_threshold(model, prep, df, y_true) -> float:
    """
    在全部数据上计算 Youden 最优决策阈值。

    Parameters
    ----------
    model : MLPClassifier
    prep : Preprocessor
    df : pd.DataFrame (需包含 prep.feature_cols, 已做年龄过滤和性别编码)
    y_true : np.ndarray (0/1)

    Returns
    -------
    float : 最优阈值
    """
    from sklearn.metrics import roc_curve

    X_imp = prep.imputer.transform(df[prep.feature_cols])
    X_scaled = prep.scaler.transform(X_imp)

    with torch.no_grad():
        x = torch.tensor(X_scaled, dtype=torch.float32).to(DEVICE)
        logits = model(x).squeeze(-1).cpu().numpy()
        probs = 1.0 / (1.0 + np.exp(-logits))

    fpr, tpr, thresholds = roc_curve(y_true, probs)
    best = thresholds[(tpr - fpr).argmax()]
    return float(best)


def _format_result_json(prob: float, threshold: float, auc: float) -> dict:
    """将概率转为结构化 JSON 结果（供移动端/小程序使用）。"""
    risk_pct = prob * 100

    if risk_pct < 5:
        level, color, level_code = "低风险", "#7EB89C", 1
        advice = "您的糖尿病风险处于极低水平。建议保持健康生活方式，定期体检即可。"
    elif risk_pct < threshold * 100:
        level, color, level_code = "中等风险", "#E2B85A", 2
        advice = (f"糖尿病风险处于临界范围，尚未超过筛查阈值 ({threshold*100:.0f}%)。"
                  f"建议关注血糖变化，定期复查。")
    elif risk_pct < 50:
        level, color, level_code = "较高风险", "#E2936B", 3
        advice = (f"糖尿病风险偏高，已超过筛查阈值 ({threshold*100:.0f}%)。"
                  f"强烈建议就医进行糖耐量试验 (OGTT) 以明确诊断。")
    elif risk_pct < 80:
        level, color, level_code = "高风险", "#D4756B", 4
        advice = "糖尿病风险处于较高水平。请尽快就医，进行全面的糖尿病筛查和并发症评估。"
    else:
        level, color, level_code = "极高风险", "#C0504A", 5
        advice = "糖尿病风险极高。请立即就医！建议进行空腹血糖、HbA1c、OGTT 等全面检查。"

    return {
        "risk_probability": round(risk_pct, 1),
        "risk_level": level,
        "risk_level_code": level_code,
        "risk_color": color,
        "advice": advice,
        "threshold_pct": round(threshold * 100, 1),
        "model_auc": round(auc, 4),
        "data_source": "NHANES 2017-2020",
    }


# =====================================================================
# 内部函数
# =====================================================================
def _encode_gender(gender: str) -> int:
    if gender == "男性":
        return 0
    elif gender == "女性":
        return 1
    return 1


def _infer(model, features_scaled: np.ndarray) -> float:
    """执行推理，返回概率值。"""
    with torch.no_grad():
        x = torch.tensor(features_scaled, dtype=torch.float32).to(DEVICE)
        logit = model(x).item()
        return float(1.0 / (1.0 + np.exp(-logit)))


def _format_result(prob: float, threshold: float, auc: float) -> str:
    """将概率转为分级 HTML 结果。"""
    risk_pct = prob * 100

    if risk_pct < 5:
        level, color, bg = "低风险", "#7EB89C", "#EDF5F1"
        advice = "您的糖尿病风险处于极低水平。建议保持健康生活方式，定期体检即可。"
        level_icon = "🟢"
    elif risk_pct < threshold * 100:
        level, color, bg = "中等风险", "#E2B85A", "#FDF8EE"
        advice = (f"糖尿病风险处于临界范围，尚未超过筛查阈值 ({threshold*100:.0f}%)。"
                  f"建议关注血糖变化，定期复查。")
        level_icon = "🟡"
    elif risk_pct < 50:
        level, color, bg = "较高风险", "#E2936B", "#FDF3ED"
        advice = (f"糖尿病风险偏高，已超过筛查阈值 ({threshold*100:.0f}%)。"
                  f"强烈建议就医进行糖耐量试验 (OGTT) 以明确诊断。")
        level_icon = "🟠"
    elif risk_pct < 80:
        level, color, bg = "高风险", "#D4756B", "#FDF0EF"
        advice = "糖尿病风险处于较高水平。请尽快就医，进行全面的糖尿病筛查和并发症评估。"
        level_icon = "🔴"
    else:
        level, color, bg = "极高风险", "#C0504A", "#FEF0EF"
        advice = "糖尿病风险极高。请立即就医！建议进行空腹血糖、HbA1c、OGTT 等全面检查。"
        level_icon = "⛔"

    return f"""
<h2>筛查评估报告</h2>

<div style="text-align:center; padding:28px 24px; background:{bg}; border-radius:16px;
            border:1.5px solid {color};">

<p style="font-size:1.15rem; font-weight:700; color:{color}; margin:0 0 4px;">
  {level_icon} {level}
</p>

<p class="prob-number" style="color:{color};">{risk_pct:.1f}%</p>
<p style="font-size:0.85rem; color:#8E8984; margin:-6px 0 12px;">糖尿病风险概率</p>

<div class="bar-bg">
  <div class="bar-fill" style="background:{color}; width:{min(risk_pct, 100)}%;"></div>
</div>

<p class="result-desc">{advice}</p>

<hr>
<small>模型 AUC: {auc:.4f} &nbsp;|&nbsp; 筛查阈值: {threshold*100:.0f}% &nbsp;|&nbsp; NHANES 2017–2020</small>
<small>⚠ 本工具仅供筛查参考，不构成医疗诊断。请咨询专业医生。</small>

</div>
"""

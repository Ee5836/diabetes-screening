import numpy as np
import pandas as pd
import os
from functools import reduce
from typing import List, Optional, Dict

# 核心变量名映射：在不同周期中，这些变量名保持不变
VARIABLE_MAP = {
    "demo": {
        "file_pattern": "DEMO",  # 人口学文件通常包含 DEMO
        "variables": ["SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH3"]
    },
    "glucose": {
        "file_pattern": "GLU",  # 空腹血糖
        "variables": ["SEQN", "LBDGLUSI"]  # 空腹血糖值(mmol/L)
    },
    "hba1c": {
        "file_pattern": "GHB",  # 糖化血红蛋白
        "variables": ["SEQN", "LBXGH"]  # HbA1c(%)
    },
    "diabetes_q": {
        "file_pattern": "DIQ",  # 糖尿病问卷
        "variables": ["SEQN", "DIQ010", "DIQ050", "DIQ070"]
    },
    "bmi": {
        "file_pattern": "BMX",  # 身体测量
        "variables": ["SEQN", "BMXBMI"]
    },
    "insulin": {
        "file_pattern": "INS",  # 空腹胰岛素
        "variables": ["SEQN", "LBXIN"]  # 空腹胰岛素 (uU/mL)
    },
    "albumin_cr": {
        "file_pattern": "ALB_CR",  # 尿白蛋白/肌酐比
        "variables": ["SEQN", "URDACT"]  # 白蛋白肌酐比值 (mg/g)
    },
    "blood_pressure": {
        "file_pattern": "BPXO",  # 血压 (示波法)
        "variables": ["SEQN", "BPXOSY1", "BPXODI1", "BPXOSY2",
                      "BPXODI2", "BPXOSY3", "BPXODI3"]
    },
    "biopro": {
        "file_pattern": "BIOPRO",  # 生化全套
        "variables": ["SEQN", "LBXSTR", "LBXSCR", "LBXSGTSI",
                      "LBXSUA", "LBXSATSI", "LBXSTB"]
    },
    "vitamin_d": {
        "file_pattern": "VID",  # 维生素
        "variables": ["SEQN", "LBXVD3MS"]  # 维生素D3 (nmol/L)
    }
}


def read_xpt(file_path: str) -> pd.DataFrame:
    """读取单个XPT文件并返回DataFrame"""
    try:
        df = pd.read_sas(file_path, format='xport', encoding='utf-8')
        # 统一将列名转为大写，避免大小写不匹配
        df.columns = df.columns.str.upper()
        return df
    except Exception as e:
        raise IOError(f"读取文件 {file_path} 失败: {e}")


def find_files_by_pattern(directory: str, pattern: str) -> List[str]:
    """
    在指定目录中查找包含特定模式字符串的XPT文件。
    例如 pattern='DEMO' 会匹配 'DEMO_H.XPT', 'DEMO_I.XPT'等。
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"目录不存在: {directory}")
    xpt_files = [f for f in os.listdir(directory) if f.upper().endswith('.XPT')]
    matched = [os.path.join(directory, f) for f in xpt_files if pattern.upper() in f.upper()]
    if not matched:
        print(f"警告: 在 {directory} 中未找到包含 '{pattern}' 的XPT文件")
    return matched


def load_and_merge_cycle(cycle_dir: str, selected_domains: Optional[List[str]] = None) -> pd.DataFrame:
    """
    加载一个NHANES周期内的所有相关XPT文件，并按SEQN合并。

    Parameters
    ----------
    cycle_dir : str
        存放某个周期所有XPT文件的目录路径
    selected_domains : list, optional
        要加载的数据域，例如 ['demo', 'glucose', 'hba1c', 'diabetes_q', 'bmi']
        默认为全部核心域。

    Returns
    -------
    pd.DataFrame
        合并后的数据框，包含所有选定域的变量。
    """
    if selected_domains is None:
        selected_domains = list(VARIABLE_MAP.keys())

    data_frames = {}

    for domain in selected_domains:
        if domain not in VARIABLE_MAP:
            print(f"未知域 '{domain}'，已跳过")
            continue

        cfg = VARIABLE_MAP[domain]
        files = find_files_by_pattern(cycle_dir, cfg["file_pattern"])

        if not files:
            # 有些周期可能没有某些文件（如OGTT），可跳过
            print(f"域 '{domain}' 无对应文件，跳过")
            continue

        # 如果一个模式匹配到多个文件（通常只有一个），取第一个
        # 实际NHANES一个周期每个域只有一个XPT文件
        file_path = files[0]
        print(f"正在加载 {domain}: {os.path.basename(file_path)}")
        df = read_xpt(file_path)

        # 只保留我们需要的变量（这些变量大概率存在）
        available_vars = [v for v in cfg["variables"] if v in df.columns]
        if 'SEQN' not in available_vars:
            raise ValueError(f"文件中缺少SEQN列: {file_path}")

        data_frames[domain] = df[available_vars]

    if not data_frames:
        raise ValueError("没有成功加载任何数据域，请检查目录和文件。")

    # 按SEQN左连接合并所有数据框
    merged = reduce(lambda left, right: pd.merge(left, right, on='SEQN', how='left'),
                    data_frames.values())

    return merged


def generate_diabetes_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    基于医学检测和问卷数据，生成糖尿病状态分类标签。

    添加三列：
    - DIABETES_STATUS: 分类标签 ('已确诊糖尿病', '未确诊糖尿病', '糖尿病前期', '正常')
    - DIABETES_GROUP: 二分类标签 (1=糖尿病, 0=非糖尿病)
    - DIABETES_UNDIAGNOSED: 是否未确诊糖尿病 (1=是, 0=否)

    Parameters
    ----------
    df : pd.DataFrame
        必须包含 DIQ010, LBDGLUSI, LBXGH, LBDGLTSI 等列(如果存在)。

    Returns
    -------
    pd.DataFrame
        添加标签后的数据框。
    """
    df = df.copy()

    # 初始化标签为'正常'
    df['DIABETES_STATUS'] = '正常'

    # 已确诊：问卷中医生告知患有糖尿病，或正在使用降糖药/胰岛素
    if 'DIQ010' in df.columns:
        diagnosed = (df['DIQ010'] == 1)
    else:
        diagnosed = pd.Series(False, index=df.index)

    if 'DIQ050' in df.columns:
        on_insulin = (df['DIQ050'] == 1)
    else:
        on_insulin = pd.Series(False, index=df.index)

    if 'DIQ070' in df.columns:
        on_meds = (df['DIQ070'] == 1)
    else:
        on_meds = pd.Series(False, index=df.index)

    diagnosed = diagnosed | on_insulin | on_meds
    df.loc[diagnosed, 'DIABETES_STATUS'] = '已确诊糖尿病'

    # 未确诊糖尿病：满足实验室指标但未确诊
    # 空腹血糖 >= 7.0 mmol/L
    cond_fpg = df['LBDGLUSI'] >= 7.0 if 'LBDGLUSI' in df.columns else pd.Series(False, index=df.index)
    # HbA1c >= 6.5%
    cond_a1c = df['LBXGH'] >= 6.5 if 'LBXGH' in df.columns else pd.Series(False, index=df.index)
    # OGTT 2h >= 11.1 mmol/L
    cond_ogtt = df['LBDGLTSI'] >= 11.1 if 'LBDGLTSI' in df.columns else pd.Series(False, index=df.index)

    undiagnosed = (~diagnosed) & (cond_fpg | cond_a1c | cond_ogtt)
    df.loc[undiagnosed, 'DIABETES_STATUS'] = '未确诊糖尿病'

    # 糖尿病前期：不满足上述条件，但处于临界范围
    pre_fpg = (df['LBDGLUSI'] >= 5.6) & (df['LBDGLUSI'] < 7.0) if 'LBDGLUSI' in df.columns else pd.Series(False,
                                                                                                          index=df.index)
    pre_a1c = (df['LBXGH'] >= 5.7) & (df['LBXGH'] < 6.5) if 'LBXGH' in df.columns else pd.Series(False, index=df.index)
    pre_ogtt = (df['LBDGLTSI'] >= 7.8) & (df['LBDGLTSI'] < 11.1) if 'LBDGLTSI' in df.columns else pd.Series(False,
                                                                                                            index=df.index)

    prediabetic = (~diagnosed & ~undiagnosed) & (pre_fpg | pre_a1c | pre_ogtt)
    df.loc[prediabetic, 'DIABETES_STATUS'] = '糖尿病前期'

    # 二分类标签：已确诊+未确诊
    df['DIABETES_GROUP'] = ((df['DIABETES_STATUS'] == '已确诊糖尿病') |
                            (df['DIABETES_STATUS'] == '未确诊糖尿病')).astype(int)

    # 未诊断糖尿病标识（在研究中有特殊意义）
    df['DIABETES_UNDIAGNOSED'] = (df['DIABETES_STATUS'] == '未确诊糖尿病').astype(int)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    在合并后的数据上构造临床衍生特征。

    新增列:
      - HOMA_IR : 胰岛素抵抗指数 = (空腹血糖 mmol/L * 胰岛素 uU/mL) / 22.5
      - BP_SYS_AVG: 三次收缩压均值 (mmHg)
      - BP_DIA_AVG: 三次舒张压均值 (mmHg)
      - EGFR     : 估算肾小球滤过率 (CKD-EPI 2021, mL/min/1.73m²)

    Parameters
    ----------
    df : pd.DataFrame
        合并后的数据框 (需包含 LBDGLUSI, LBXIN, BPXOSY*, BPXODI*,
        LBXSCR, RIAGENDR, RIDAGEYR)

    Returns
    -------
    pd.DataFrame
        添加衍生特征后的数据框
    """
    df = df.copy()

    # ---- HOMA-IR: 胰岛素抵抗指数 ----
    # 仅当同时有 空腹血糖 和 胰岛素 时计算
    if 'LBDGLUSI' in df.columns and 'LBXIN' in df.columns:
        mask = df['LBDGLUSI'].notna() & df['LBXIN'].notna()
        # HOMA-IR = (glucose_mmol/L * insulin_uU/mL) / 22.5
        df['HOMA_IR'] = np.where(
            mask,
            (df['LBDGLUSI'] * df['LBXIN']) / 22.5,
            np.nan
        )
    else:
        df['HOMA_IR'] = np.nan

    # ---- 平均血压 ----
    sys_cols = [c for c in ['BPXOSY1', 'BPXOSY2', 'BPXOSY3'] if c in df.columns]
    dia_cols = [c for c in ['BPXODI1', 'BPXODI2', 'BPXODI3'] if c in df.columns]
    if sys_cols:
        df['BP_SYS_AVG'] = df[sys_cols].mean(axis=1, skipna=True)
    else:
        df['BP_SYS_AVG'] = np.nan
    if dia_cols:
        df['BP_DIA_AVG'] = df[dia_cols].mean(axis=1, skipna=True)
    else:
        df['BP_DIA_AVG'] = np.nan

    # ---- eGFR (CKD-EPI 2021 公式) ----
    # 需要: 血清肌酐 (LBXSCR), 年龄, 性别
    if 'LBXSCR' in df.columns:
        scr = df['LBXSCR'].values  # mg/dL
        age = df['RIDAGEYR'].values
        is_female = (df['RIAGENDR'] == 2).values if 'RIAGENDR' in df.columns else np.zeros(len(df))

        # kappa: 0.7 (female), 0.9 (male)
        kappa = np.where(is_female, 0.7, 0.9)
        # alpha: -0.241 (female), -0.302 (male)
        alpha = np.where(is_female, -0.241, -0.302)
        # sex_factor: 1.012

        scr_kappa = np.minimum(scr / kappa, 1.0)
        scr_kappa_alpha = scr_kappa ** alpha
        max_term = np.maximum(scr / kappa, 1.0) ** (-1.200)
        age_power = 0.9938 ** age
        sex_factor = np.where(is_female, 1.012, 1.0)

        egfr = 142.0 * scr_kappa_alpha * max_term * age_power * sex_factor

        # 标记不可靠估算
        mask_valid = pd.Series(scr).notna() & pd.Series(age).notna()
        df['EGFR'] = np.where(mask_valid, egfr, np.nan)
    else:
        df['EGFR'] = np.nan

    return df


# 可选：如果有网络需求，可扩展下载功能，但一般手动下载更稳定
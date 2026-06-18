"""
==========================================================================
NHANES 糖尿病数据集构建脚本 (v2 — 扩展版)
==========================================================================
基于 2017-March 2020 周期的 XPT 原始数据，合并多域变量、构造衍生特征、
生成糖尿病分类标签。

数据域 (11个):
  - DEMO     (人口学)     : SEQN, RIAGENDR, RIDAGEYR, RIDRETH3
  - GLU      (空腹血糖)   : SEQN, LBDGLUSI (mmol/L)
  - GHB      (HbA1c)      : SEQN, LBXGH (%)
  - DIQ      (糖尿病问卷) : SEQN, DIQ010, DIQ050, DIQ070
  - BMX      (身体测量)   : SEQN, BMXBMI
  - INS      (空腹胰岛素) : SEQN, LBXIN (uU/mL)
  - ALB_CR   (尿白蛋白)   : SEQN, URDACT (mg/g)
  - BPXO     (血压)       : SEQN, 3次收缩压/舒张压
  - BIOPRO   (生化全套)   : SEQN, LBXSTR, LBXSCR, LBXSGTSI, LBXSUA, LBXSATSI, LBXSTB
  - VID      (维生素D)    : SEQN, LBXVD3MS (nmol/L)

衍生特征:
  - HOMA_IR   : 胰岛素抵抗指数
  - BP_SYS_AVG: 平均收缩压
  - BP_DIA_AVG: 平均舒张压
  - EGFR      : 估算肾小球滤过率 (CKD-EPI 2021)

输出标签:
  - DIABETES_STATUS      : 已确诊糖尿病 / 未确诊糖尿病 / 糖尿病前期 / 正常
  - DIABETES_GROUP       : 1=糖尿病, 0=非糖尿病
  - DIABETES_UNDIAGNOSED : 1=未确诊糖尿病, 0=否
==========================================================================
"""

import sys
import os
import pandas as pd

# 确保可以从项目根目录或 scripts/ 目录运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_and_merge_cycle, generate_diabetes_labels, engineer_features

# =========================== 配置 ===========================
DATA_DIR = "./dataset"           # XPT 原始文件目录
OUTPUT_DIR = "./output"          # 合成数据集输出目录
OUTPUT_NAME = "nhanes_diabetes_2020_2023_v2.csv"

# =========================== 合成 ===========================
def main():
    print("=" * 60)
    print("NHANES 糖尿病数据集构建 (v2 — 扩展版)")
    print("=" * 60)

    # 1. 加载并合并全部 11 个数据域
    print(f"\n[1/4] 从 {DATA_DIR} 加载 XPT 文件...")
    all_domains = ['demo', 'glucose', 'hba1c', 'diabetes_q', 'bmi',
                   'insulin', 'albumin_cr', 'blood_pressure', 'biopro', 'vitamin_d']
    df = load_and_merge_cycle(DATA_DIR, selected_domains=all_domains)
    print(f"合并完成: {df.shape[0]} 行 × {df.shape[1]} 列")

    # 2. 构造衍生特征 (HOMA-IR, eGFR, 平均血压)
    print("\n[2/4] 构造衍生特征 (HOMA-IR, eGFR, 平均血压)...")
    df = engineer_features(df)
    new_cols = [c for c in ['HOMA_IR', 'BP_SYS_AVG', 'BP_DIA_AVG', 'EGFR'] if c in df.columns]
    print(f"  新增列: {new_cols}")

    # 3. 生成糖尿病标签
    print("\n[3/4] 生成糖尿病分类标签...")
    df_labeled = generate_diabetes_labels(df)

    # 4. 保存结果
    print(f"\n[4/4] 保存数据集...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_NAME)
    df_labeled.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"已保存至: {output_path}")

    # =========================== 简报 ===========================
    print("\n" + "=" * 60)
    print("数据集预览")
    print("=" * 60)
    print(f"\n形状: {df_labeled.shape[0]} 行 × {df_labeled.shape[1]} 列")
    print(f"列名: {list(df_labeled.columns)}")

    print("\n--- DIABETES_STATUS 分布 ---")
    status_counts = df_labeled['DIABETES_STATUS'].value_counts()
    for label, count in status_counts.items():
        pct = count / len(df_labeled) * 100
        print(f"  {label}:  {count:>6}  ({pct:.1f}%)")

    print("\n--- DIABETES_GROUP 分布 (1=糖尿病) ---")
    group_counts = df_labeled['DIABETES_GROUP'].value_counts()
    for label, count in group_counts.items():
        pct = count / len(df_labeled) * 100
        print(f"  {label}:  {count:>6}  ({pct:.1f}%)")

    print("\n--- 新增特征缺失率 ---")
    for c in new_cols:
        miss = df_labeled[c].isna().sum()
        pct = miss / len(df_labeled) * 100
        print(f"  {c}: 缺失 {miss} ({pct:.1f}%)")

    print("\n构建完成!")


if __name__ == "__main__":
    main()

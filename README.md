# 糖尿病自测

基于 **NHANES 2020–2023** 临床数据的深度学习糖尿病风险评估工具，提供 Flask API + 微信小程序双端支持。

---

## 项目结构

```
├── dataset/                          # 原始 NHANES XPT 文件 (11 个域)
├── scripts/                          # 数据处理 & 训练脚本
│   ├── utils.py                      # 数据加载 / 特征工程 / 标签生成
│   ├── build_dataset.py              # 构建结构化数据集
│   ├── train.py                      # 模型训练
│   └── analyze.py                    # 可视化分析
├── output/                           # 数据集 / 模型 / 图表
│   ├── nhanes_diabetes_2017_2020_v2.csv
│   ├── models/                       # PyTorch 模型权重
│   └── figures/                      # 评估图表
├── app/                              # Flask 后端
│   ├── config.py                     # 全局配置
│   ├── model.py                      # MLP 模型定义 & 加载
│   ├── preprocess.py                 # 预处理器
│   ├── inference.py                  # 推理 & 结果格式化
│   ├── main.py                       # Flask 入口 & API
│   ├── templates/index.html          # Web 界面
│   └── static/                       # CSS / JS
├── miniapp/                          # 微信小程序
│   ├── app.js / app.json / app.wxss  # 全局配置 & 样式
│   ├── pages/index/                  # 主页面
│   ├── components/                   # 组件
│   │   ├── form-basic/               # 基础筛查表单 (6 字段)
│   │   ├── form-advanced/            # 深度筛查表单 (16 字段)
│   │   ├── result-card/              # 结果卡片
│   │   └── help-panel/               # 使用说明
│   └── utils/                        # 工具函数
│       ├── config.js                 # API 地址 & 输入约束
│       ├── api.js                    # 网络请求封装
│       └── validator.js              # 客户端输入校验
├── run.py                            # 一键启动后端
├── requirements.txt                  # Python 依赖
└── README.md
```

---

## 快速开始

### 环境要求

- Python ≥ 3.8
- PyTorch ≥ 1.12
- 微信开发者工具（小程序端）

### 安装

```bash
pip install -r requirements.txt
```

### 数据构建 (可选)

```bash
python scripts/build_dataset.py
```

输出: `output/nhanes_diabetes_2020_2023_v2.csv`

### 模型训练 (可选，已提供预训练权重)

```bash
python scripts/train.py
```

### 启动后端

```bash
python run.py
```

后端运行在 `http://0.0.0.0:7861`

### 启动小程序

1. 打开微信开发者工具
2. 导入项目 → 选择 `miniapp/` 目录
3. 设置 → 勾选「不校验合法域名」
4. 修改 `miniapp/utils/config.js` 中 `API_BASE_URL` 为后端地址

---

## 模型

### 架构

```
MLP Classifier (~46K params)
├── Linear(input → 256) → BatchNorm → ReLU → Dropout(0.3)
├── Linear(256 → 128)  → BatchNorm → ReLU → Dropout(0.3)
├── Linear(128 → 64)   → BatchNorm → ReLU → Dropout(0.3)
└── Linear(64 → 1)     → Sigmoid
```

### 特征集

| 特征集 | 字段数 | AUC |
|--------|--------|-----|
| feat6 (基础) | 6 | 0.9222 |
| feat_extended (深度) | 16 | 0.9322 |
| feat_all | 22 | — |
| multiclass | 16 (4分类) | — |

### 标签定义

| 类别 | 标准 |
|------|------|
| 已确诊糖尿病 | 医生诊断 或 使用降糖药/胰岛素 |
| 未确诊糖尿病 | FPG ≥ 7.0 mmol/L 或 HbA1c ≥ 6.5% |
| 糖尿病前期 | FPG 5.6–7.0 或 HbA1c 5.7–6.5% |
| 正常 | 均不满足 |

---

## API

### Health Check

```bash
GET /api/health
# { "status": "ok", "service": "糖尿病风险筛查 API" }
```

### 基础筛查

```bash
POST /api/predict/basic
Content-Type: application/json

{
  "age": 45, "gender": "男性", "race": "非西班牙裔亚裔",
  "hba1c": 5.5, "fasting_glucose": 5.5, "bmi": 25.0
}
```

### 深度筛查

```bash
POST /api/predict/advanced
Content-Type: application/json

{
  "age": 45, "gender": "男性", "race": "非西班牙裔亚裔",
  "hba1c": 5.5, "fasting_glucose": 5.5, "bmi": 25.0,
  "homa_ir": null, "egfr": null, "urdact": null,
  "bp_sys": null, "bp_dia": null, "triglyc": null,
  "ggt": null, "uric_acid": null, "alt": null, "vit_d3": null
}
```

可选字段传 `null` 或留空，后端自动使用健康人群参考值填补。

---

## 小程序功能

| 标签 | 功能 |
|------|------|
| 基础筛查 | 年龄 + 性别 + HbA1c + 空腹血糖 + 身高体重 |
| 深度筛查 | 基础 + 10 项进阶指标（肾功能、胰岛素抵抗、血压、血脂、肝酶、维生素D3） |
| 使用说明 | 字段解释 + 风险等级对照表 + 免责声明 |

---

## 风险等级

| 等级 | 概率 | 建议 |
|------|------|------|
| 🟢 低风险 | < 5% | 保持健康生活方式 |
| 🟡 中等风险 | 5% ~ 阈值 | 关注血糖，定期复查 |
| 🟠 较高风险 | 阈值 ~ 50% | 建议做 OGTT 确诊 |
| 🔴 高风险 | 50% ~ 80% | 尽快就医筛查 |
| ⛔ 极高风险 | > 80% | 立即全面检查 |

---

## 数据来源

| 特征 | NHANES 变量 |
|------|------------|
| 人口学 | `RIAGENDR`, `RIDAGEYR`, `RIDRETH3` |
| 空腹血糖 | `LBDGLUSI` |
| HbA1c | `LBXGH` |
| BMI | `BMXBMI` |
| 胰岛素 | `LBXIN` → HOMA-IR (衍生) |
| 肾功能 | `LBXSCR` → eGFR CKD-EPI 2021 (衍生) |
| 尿蛋白 | `URDACT` |
| 血压 | `BPXOSY1-3`, `BPXODI1-3` → 均值 |
| 甘油三酯 | `LBXSTR` |
| 肝酶 | `LBXSGTSI` (GGT), `LBXSATSI` (ALT) |
| 尿酸 | `LBXSUA` |
| 维生素 D3 | `LBXVD3MS` |

---

## 免责声明

本工具仅供健康风险筛查参考，**不构成医疗诊断**。如有任何健康疑虑，请及时前往正规医疗机构就诊。

---

## 参考文献

- NHANES Data: [CDC/NCHS](https://wwwn.cdc.gov/nchs/nhanes/)
- CKD-EPI 2021: Inker LA, et al. *N Engl J Med* 2021
- HOMA-IR: Matthews DR, et al. *Diabetologia* 1985

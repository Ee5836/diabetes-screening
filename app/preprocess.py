"""
预处理器
========
拟合 Imputer + Scaler，提供特征到数值的转换。
"""
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from .config import DATA_PATH, FEAT6_COLS, FEAT16_COLS


class Preprocessor:
    """封装 Imputer + StandardScaler 的预处理器。"""

    def __init__(self, feature_cols: list, strategy: str = "median"):
        """
        Parameters
        ----------
        feature_cols : list[str]
            特征列名列表
        strategy : str
            填补策略，默认 median
        """
        self.feature_cols = feature_cols
        self.imputer = SimpleImputer(strategy=strategy)
        self.scaler = StandardScaler()
        self.medians: dict = {}
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "Preprocessor":
        """在训练数据上拟合预处理器。"""
        X = df[self.feature_cols].copy()
        X_imp = self.imputer.fit_transform(X)
        self.scaler.fit(X_imp)

        # 保存中位数用于缺失值自动填充
        stats = self.imputer.statistics_
        self.medians = {self.feature_cols[i]: float(stats[i])
                        for i in range(len(self.feature_cols))}
        self._fitted = True
        return self

    def transform(self, features: np.ndarray) -> np.ndarray:
        """对特征数组进行填补 + 标准化。"""
        if not self._fitted:
            raise RuntimeError("预处理器尚未拟合，请先调用 fit()。")
        imp = self.imputer.transform(features)
        return self.scaler.transform(imp)

    def fill_missing(self, raw_values: dict) -> np.ndarray:
        """
        从原始字典构建特征数组，缺失值用中位数填充。

        Parameters
        ----------
        raw_values : dict
            {列名: 数值或 None}

        Returns
        -------
        np.ndarray shape (1, n_features)
        """
        vals = []
        for col in self.feature_cols:
            v = raw_values.get(col)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                v = self.medians.get(col, 0.0)
            vals.append(float(v))
        return np.array([vals], dtype=np.float32)


def build_preprocessors() -> tuple:
    """
    从全部数据拟合预处理器并返回 (preprocessor_6, preprocessor_16)。

    同时返回 (y_true, probs6, probs16) 用于后续阈值计算。
    """
    print("  加载数据 & 拟合预处理器...")
    df = pd.read_csv(DATA_PATH)
    df = df[df["RIDAGEYR"] >= 8].copy()
    df["RIAGENDR"] = df["RIAGENDR"].map({1: 0, 2: 1})

    # 基础 6 特征
    prep6 = Preprocessor(FEAT6_COLS)
    prep6.fit(df)
    print(f"    feat6: {len(FEAT6_COLS)} 特征, 预处理器就绪")

    # 扩展 16 特征
    prep16 = Preprocessor(FEAT16_COLS)
    prep16.fit(df)
    print(f"    feat16: {len(FEAT16_COLS)} 特征, 预处理器就绪")

    # 返回 df 用于阈值计算
    y_true = (df["DIABETES_GROUP"] == 1).values.astype(np.float32)

    return prep6, prep16, df, y_true

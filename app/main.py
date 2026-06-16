"""
入口模块
========
1. 加载模型 + 预处理器
2. 计算最优阈值
3. 启动 Flask Web 服务
"""
from functools import partial

from flask import Flask, render_template, request, jsonify

from .config import (
    DEVICE, FEAT6_COLS, FEAT16_COLS,
    AUC_BASELINE, AUC_EXTENDED,
    SERVER_HOST, SERVER_PORT,
)
from .model import load_model
from .preprocess import build_preprocessors
from .inference import (
    predict_basic, predict_basic_json,
    predict_advanced, predict_advanced_json,
    compute_optimal_threshold,
)

# ---- 全局变量 (启动时初始化) ----
_app = None
_prep6 = None
_prep16 = None
_model6 = None
_model16 = None
_thresh6 = None
_thresh16 = None
_fn_basic = None
_fn_advanced = None
_fn_basic_json = None
_fn_advanced_json = None


def _validate_numeric(value, name: str, min_val: float, max_val: float) -> list:
    """校验单个数值参数，返回错误列表。"""
    errors = []
    if value is None or value == "":
        return errors  # 可选字段允许为空
    try:
        v = float(value)
        if v < min_val:
            errors.append(f"{name} 值 {v} 低于最小值 {min_val}")
        if v > max_val:
            errors.append(f"{name} 值 {v} 超过最大值 {max_val}")
    except (ValueError, TypeError):
        errors.append(f"{name} 格式错误: {value}")
    return errors


def create_app() -> Flask:
    """创建并配置 Flask 应用。"""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # 开发阶段禁用静态文件缓存
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.after_request
    def _add_headers(response):
        # 禁用缓存
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # CORS (微信小程序开发调试用，生产环境应限制 origin)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        return response

    # ---- Health Check ----
    @app.route("/api/health", methods=["GET"])
    def api_health():
        return jsonify({"status": "ok", "service": "糖尿病风险筛查 API"})

    # ---- API: 基础筛查 ----
    @app.route("/api/predict/basic", methods=["POST"])
    def api_predict_basic():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"code": 400, "message": "请求体不能为空", "data": None}), 400

        # 输入验证
        errors = []
        errors += _validate_numeric(data.get("age"), "年龄", 8, 80)
        errors += _validate_numeric(data.get("hba1c"), "HbA1c", 3.0, 18.0)
        errors += _validate_numeric(data.get("fasting_glucose"), "空腹血糖", 2.5, 30.0)
        errors += _validate_numeric(data.get("bmi"), "BMI", 12.0, 65.0)
        if errors:
            return jsonify({"code": 400, "message": "; ".join(errors), "data": None}), 400

        try:
            age = float(data.get("age", 45))
            gender = str(data.get("gender", "男性"))
            race = str(data.get("race", "非西班牙裔白人"))
            hba1c = float(data.get("hba1c", 5.5))
            fasting_glucose = float(data.get("fasting_glucose", 5.5))
            bmi = float(data.get("bmi", 25.0))
        except (ValueError, TypeError) as e:
            return jsonify({"code": 400, "message": f"参数解析错误: {e}", "data": None}), 400

        result = _fn_basic_json(age, gender, race, hba1c, fasting_glucose, bmi)
        return jsonify({"code": 0, "message": "success", "data": result})

    # ---- API: 深度筛查 ----
    @app.route("/api/predict/advanced", methods=["POST"])
    def api_predict_advanced():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"code": 400, "message": "请求体不能为空", "data": None}), 400

        # 输入验证（必填字段）
        errors = []
        errors += _validate_numeric(data.get("age"), "年龄", 8, 80)
        errors += _validate_numeric(data.get("hba1c"), "HbA1c", 3.0, 18.0)
        errors += _validate_numeric(data.get("fasting_glucose"), "空腹血糖", 2.5, 30.0)
        errors += _validate_numeric(data.get("bmi"), "BMI", 12.0, 65.0)
        # 可选字段：仅当提供了值时才校验
        errors += _validate_numeric(data.get("homa_ir"), "HOMA-IR", 0.0, 50.0)
        errors += _validate_numeric(data.get("egfr"), "eGFR", 10.0, 200.0)
        errors += _validate_numeric(data.get("urdact"), "尿白蛋白/肌酐比", 0.0, 5000.0)
        errors += _validate_numeric(data.get("bp_sys"), "收缩压", 70.0, 250.0)
        errors += _validate_numeric(data.get("bp_dia"), "舒张压", 30.0, 150.0)
        errors += _validate_numeric(data.get("triglyc"), "甘油三酯", 20.0, 2000.0)
        errors += _validate_numeric(data.get("ggt"), "GGT", 2.0, 2000.0)
        errors += _validate_numeric(data.get("uric_acid"), "尿酸", 1.0, 15.0)
        errors += _validate_numeric(data.get("alt"), "ALT", 3.0, 500.0)
        errors += _validate_numeric(data.get("vit_d3"), "维生素D3", 3.0, 500.0)
        if errors:
            return jsonify({"code": 400, "message": "; ".join(errors), "data": None}), 400

        try:
            age = float(data.get("age", 45))
            gender = str(data.get("gender_adv", data.get("gender", "男性")))
            race = str(data.get("race", "非西班牙裔白人"))
            hba1c = float(data.get("hba1c", 5.5))
            fasting_glucose = float(data.get("fasting_glucose", 5.5))
            bmi = float(data.get("bmi", 25.0))

            # 进阶指标 — None 表示使用中位数
            def _opt_float(key):
                val = data.get(key)
                if val is None or val == "":
                    return None
                return float(val)

            homa_ir = _opt_float("homa_ir")
            egfr = _opt_float("egfr")
            urdact = _opt_float("urdact")
            bp_sys = _opt_float("bp_sys")
            bp_dia = _opt_float("bp_dia")
            triglyc = _opt_float("triglyc")
            ggt = _opt_float("ggt")
            uric_acid = _opt_float("uric_acid")
            alt = _opt_float("alt")
            vit_d3 = _opt_float("vit_d3")
        except (ValueError, TypeError) as e:
            return jsonify({"code": 400, "message": f"参数解析错误: {e}", "data": None}), 400

        result = _fn_advanced_json(
            age, gender, race, hba1c, fasting_glucose, bmi,
            homa_ir, egfr, urdact, bp_sys, bp_dia,
            triglyc, ggt, uric_acid, alt, vit_d3,
        )
        return jsonify({"code": 0, "message": "success", "data": result})

    # ---- 首页 ----
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


def main():
    global _prep6, _prep16, _model6, _model16, _thresh6, _thresh16
    global _fn_basic, _fn_advanced, _fn_basic_json, _fn_advanced_json

    print("=" * 50)
    print("  糖尿病风险筛查工具 - 启动中...")
    print(f"  设备: {DEVICE}")
    print("=" * 50)

    # ---- 1. 预处理器 ----
    print("\n[1/3] 拟合预处理器...")
    _prep6, _prep16, df, y_true = build_preprocessors()

    # ---- 2. 模型 ----
    print("\n[2/3] 加载模型...")
    _model6 = load_model(len(FEAT6_COLS), "best_model_feat6.pt")
    print(f"  feat6 加载完成 ({sum(p.numel() for p in _model6.parameters()):,} params)")

    _model16 = load_model(len(FEAT16_COLS), "best_model_feat_extended.pt")
    print(f"  feat16 加载完成 ({sum(p.numel() for p in _model16.parameters()):,} params)")

    # ---- 3. 最优阈值 ----
    print("\n[3/3] 计算最优决策阈值...")
    _thresh6 = compute_optimal_threshold(_model6, _prep6, df, y_true)
    print(f"  feat6 阈值: {_thresh6:.4f}")

    _thresh16 = compute_optimal_threshold(_model16, _prep16, df, y_true)
    print(f"  feat16 阈值: {_thresh16:.4f}")

    # ---- 4. 绑定推理函数 ----
    _fn_basic = partial(predict_basic, _prep6, _model6, _thresh6, AUC_BASELINE)
    _fn_advanced = partial(predict_advanced, _prep16, _model16, _thresh16, AUC_EXTENDED)
    _fn_basic_json = partial(predict_basic_json, _prep6, _model6, _thresh6, AUC_BASELINE)
    _fn_advanced_json = partial(predict_advanced_json, _prep16, _model16, _thresh16, AUC_EXTENDED)

    # ---- 5. 启动 Flask ----
    print(f"\n启动 Web 界面 → http://{SERVER_HOST}:{SERVER_PORT}")
    app = create_app()
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)


if __name__ == "__main__":
    main()

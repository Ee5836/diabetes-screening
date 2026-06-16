"""
糖尿病风险筛查工具 - Web 应用模块
==================================
基于 NHANES 2017-2020 深度学习模型 (MLP ~46K params)。

子模块:
  config     - 全局配置 (路径、超参、特征列定义)
  model      - MLP 模型定义与加载
  preprocess - 预处理器 (Imputer + Scaler)
  inference  - 推理逻辑 (预测 + 结果渲染)
  main       - Flask 入口 (路由 + API)

前端:
  templates/ - Jinja2 HTML 模板
  static/    - CSS / JS 静态资源
"""

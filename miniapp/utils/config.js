/**
 * 小程序配置常量
 * ================
 */

module.exports = {
  // ---- API 地址 (开发时改为 ngrok 隧道地址) ----
  API_BASE_URL: 'https://clique-knelt-parting.ngrok-free.dev',

  // ---- 输入约束 (与服务端一致) ----
  AGE_MIN: 8,
  AGE_MAX: 80,
  BMI_MIN: 12,
  BMI_MAX: 65,

  HEIGHT_MIN: 100,
  HEIGHT_MAX: 250,
  WEIGHT_MIN: 30,
  WEIGHT_MAX: 200,

  HBA1C_MIN: 3.0,
  HBA1C_MAX: 18.0,
  GLUCOSE_MIN: 2.5,
  GLUCOSE_MAX: 30.0,

  HOMA_IR_MIN: 0.0,
  HOMA_IR_MAX: 50.0,
  EGFR_MIN: 10.0,
  EGFR_MAX: 200.0,
  URDACT_MIN: 0.0,
  URDACT_MAX: 5000.0,
  BP_SYS_MIN: 70.0,
  BP_SYS_MAX: 250.0,
  BP_DIA_MIN: 30.0,
  BP_DIA_MAX: 150.0,
  TRIGLYC_MIN: 20.0,
  TRIGLYC_MAX: 2000.0,
  GGT_MIN: 2.0,
  GGT_MAX: 2000.0,
  URIC_ACID_MIN: 1.0,
  URIC_ACID_MAX: 15.0,
  ALT_MIN: 3.0,
  ALT_MAX: 500.0,
  VIT_D3_MIN: 3.0,
  VIT_D3_MAX: 500.0,
};

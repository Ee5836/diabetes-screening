/**
 * 客户端输入校验
 * ================
 * 在提交前验证字段范围和类型，提供即时反馈。
 */

const C = require('./config');

/**
 * 校验数值是否在范围内
 * @returns {string|null} 错误消息或 null
 */
function checkRange(value, name, min, max) {
  if (value === '' || value === null || value === undefined) return null;
  const v = Number(value);
  if (isNaN(v)) return `${name} 格式不正确`;
  if (v < min) return `${name} 不能低于 ${min}`;
  if (v > max) return `${name} 不能超过 ${max}`;
  return null;
}

/**
 * 校验基础筛查表单
 */
function validateBasic(data) {
  const errors = [];
  const e = checkRange(data.age, '年龄', C.AGE_MIN, C.AGE_MAX);
  if (e) errors.push(e);
  const e2 = checkRange(data.hba1c, 'HbA1c', C.HBA1C_MIN, C.HBA1C_MAX);
  if (e2) errors.push(e2);
  const e3 = checkRange(data.fasting_glucose, '空腹血糖', C.GLUCOSE_MIN, C.GLUCOSE_MAX);
  if (e3) errors.push(e3);
  const e4 = checkRange(data.height, '身高', C.HEIGHT_MIN, C.HEIGHT_MAX);
  if (e4) errors.push(e4);
  const e5 = checkRange(data.weight, '体重', C.WEIGHT_MIN, C.WEIGHT_MAX);
  if (e5) errors.push(e5);

  return { valid: errors.length === 0, errors, data };
}

/**
 * 校验深度筛查表单
 */
function validateAdvanced(data) {
  const errors = [];
  // 必填字段
  const e = checkRange(data.age, '年龄', C.AGE_MIN, C.AGE_MAX);
  if (e) errors.push(e);
  const e2 = checkRange(data.hba1c, 'HbA1c', C.HBA1C_MIN, C.HBA1C_MAX);
  if (e2) errors.push(e2);
  const e3 = checkRange(data.fasting_glucose, '空腹血糖', C.GLUCOSE_MIN, C.GLUCOSE_MAX);
  if (e3) errors.push(e3);
  const e4 = checkRange(data.height, '身高', C.HEIGHT_MIN, C.HEIGHT_MAX);
  if (e4) errors.push(e4);
  const e5 = checkRange(data.weight, '体重', C.WEIGHT_MIN, C.WEIGHT_MAX);
  if (e5) errors.push(e5);

  // 可选字段 (仅当有值时校验)
  const optionalFields = [
    ['homa_ir', 'HOMA-IR', C.HOMA_IR_MIN, C.HOMA_IR_MAX],
    ['egfr', 'eGFR', C.EGFR_MIN, C.EGFR_MAX],
    ['urdact', '尿白蛋白/肌酐比', C.URDACT_MIN, C.URDACT_MAX],
    ['bp_sys', '收缩压', C.BP_SYS_MIN, C.BP_SYS_MAX],
    ['bp_dia', '舒张压', C.BP_DIA_MIN, C.BP_DIA_MAX],
    ['triglyc', '甘油三酯', C.TRIGLYC_MIN, C.TRIGLYC_MAX],
    ['ggt', 'GGT', C.GGT_MIN, C.GGT_MAX],
    ['uric_acid', '尿酸', C.URIC_ACID_MIN, C.URIC_ACID_MAX],
    ['alt', 'ALT', C.ALT_MIN, C.ALT_MAX],
    ['vit_d3', '维生素D3', C.VIT_D3_MIN, C.VIT_D3_MAX],
  ];
  optionalFields.forEach(([key, label, min, max]) => {
    const err = checkRange(data[key], label, min, max);
    if (err) errors.push(err);
  });

  return { valid: errors.length === 0, errors, data };
}

module.exports = { validateBasic, validateAdvanced };

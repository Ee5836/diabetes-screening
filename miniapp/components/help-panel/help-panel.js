/**
 * 使用说明面板 (纯静态内容)
 */

Component({
  properties: {},

  data: {
    // 风险等级对照表
    riskTable: [
      { level: '🟢 低风险', range: '< 5%', advice: '保持健康生活方式，定期体检' },
      { level: '🟡 中等风险', range: '5% ~ 阈值', advice: '关注血糖变化，定期复查' },
      { level: '🟠 较高风险', range: '阈值 ~ 50%', advice: '建议进行 OGTT 确诊试验' },
      { level: '🔴 高风险', range: '50% ~ 80%', advice: '尽快就医，全面筛查' },
      { level: '⛔ 极高风险', range: '> 80%', advice: '立即就医，全面检查' },
    ],
  },
});

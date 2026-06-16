/**
 * 结果卡片组件
 * 根据 risk_level_code (1-5) 渲染不同颜色等级
 */

// 等级配置
const LEVEL_CONFIG = {
  1: { bg: '#EDF5F1', icon: '🟢' },
  2: { bg: '#FDF8EE', icon: '🟡' },
  3: { bg: '#FDF3ED', icon: '🟠' },
  4: { bg: '#FDF0EF', icon: '🔴' },
  5: { bg: '#FEF0EF', icon: '⛔' },
};

Component({
  properties: {
    result: {
      type: Object,
      value: null,
    },
  },

  data: {
    bgColor: '#EDF5F1',
    levelIcon: '🟢',
    barWidth: 0,
  },

  observers: {
    'result'(val) {
      if (!val) return;
      const cfg = LEVEL_CONFIG[val.risk_level_code] || LEVEL_CONFIG[1];
      this.setData({
        bgColor: cfg.bg,
        levelIcon: cfg.icon,
        barWidth: Math.min(val.risk_probability, 100),
      });
    },
  },
});

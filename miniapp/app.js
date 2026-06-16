/**
 * 糖尿病风险筛查工具 — 微信小程序
 * ====================================
 * 全局入口
 */
App({
  onLaunch() {
    // 获取系统信息
    const systemInfo = wx.getSystemInfoSync();
    this.globalData.systemInfo = systemInfo;
  },

  globalData: {
    systemInfo: null,
    // 首次启动显示免责声明
    disclaimerAccepted: false,
  },
});

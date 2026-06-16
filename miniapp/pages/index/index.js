/**
 * 主页面 — 三标签页容器 + 免责声明弹窗
 */

const api = require('../../utils/api');
const validator = require('../../utils/validator');

Page({
  data: {
    tabs: [
      { id: 'basic', icon: '\u{1F4CB}', label: '基础筛查' },
      { id: 'advanced', icon: '\u{1F52C}', label: '深度筛查' },
      { id: 'help', icon: '\u{1F4D6}', label: '使用说明' },
    ],
    activeTab: 'basic',
    loading: false,
    showResult: false,
    resultData: null,

    // 免责声明弹窗
    showDisclaimer: true,
    agreed: false,
    countdownDone: false,
    canProceed: false,
    btnText: '',
    countdownSec: 3,
    countdownTimer: null,

    // 随机测试数据（3组）
    profiles: [
      {
        label: '低风险示例',
        age: '28', genderIndex: 1,
        hba1c: '5.1', fastingGlucose: '4.8',
        height: '160', weight: '52',
        homaIr: '1.2', egfr: '105', urdact: '8',
        bpSys: '108', bpDia: '68',
        triglyc: '85', ggt: '18', uricAcid: '4.2', alt: '16', vitD3: '65',
      },
      {
        label: '中风险示例',
        age: '52', genderIndex: 0,
        hba1c: '5.9', fastingGlucose: '6.2',
        height: '172', weight: '78',
        homaIr: '2.8', egfr: '82', urdact: '25',
        bpSys: '138', bpDia: '85',
        triglyc: '180', ggt: '42', uricAcid: '6.5', alt: '35', vitD3: '38',
      },
      {
        label: '高风险示例',
        age: '65', genderIndex: 0,
        hba1c: '7.2', fastingGlucose: '8.5',
        height: '168', weight: '92',
        homaIr: '4.5', egfr: '58', urdact: '85',
        bpSys: '155', bpDia: '95',
        triglyc: '260', ggt: '78', uricAcid: '8.2', alt: '52', vitD3: '22',
      },
    ],
  },

  onLoad() {
    this.setData({ btnText: '请阅读并勾选同意', countdownSec: 10 });
    this.startCountdown();
  },

  /** 随机填充当前表单 */
  randomFill() {
    const idx = Math.floor(Math.random() * 3);
    const profile = this.data.profiles[idx];
    const activeTab = this.data.activeTab;

    if (activeTab === 'basic') {
      const form = this.selectComponent('#formBasic');
      if (form) form.setData({
        age: profile.age, genderIndex: profile.genderIndex,
        hba1c: profile.hba1c, fastingGlucose: profile.fastingGlucose,
        height: profile.height, weight: profile.weight,
      });
    } else if (activeTab === 'advanced') {
      const form = this.selectComponent('#formAdvanced');
      if (form) form.setData({
        age: profile.age, genderIndex: profile.genderIndex,
        hba1c: profile.hba1c, fastingGlucose: profile.fastingGlucose,
        height: profile.height, weight: profile.weight,
        homaIr: profile.homaIr, egfr: profile.egfr, urdact: profile.urdact,
        bpSys: profile.bpSys, bpDia: profile.bpDia,
        triglyc: profile.triglyc, ggt: profile.ggt,
        uricAcid: profile.uricAcid, alt: profile.alt, vitD3: profile.vitD3,
      });
    }

    wx.showToast({ title: `已填充：${profile.label}`, icon: 'none', duration: 1500 });
    wx.pageScrollTo({ scrollTop: 0, duration: 300 });
  },

  /** 切换标签 — 保存全部填选数据，切换后恢复 */
  switchTab(e) {
    const from = this.data.activeTab;
    const to = e.currentTarget.dataset.tab;
    const sharedFields = ['age', 'genderIndex', 'hba1c', 'fastingGlucose', 'height', 'weight'];

    // 保存当前表单全部数据
    const fromId = from === 'basic' ? '#formBasic' : '#formAdvanced';
    const comp = this.selectComponent(fromId);
    if (comp) {
      const saved = {};
      // 共享字段 + 当前表单所有独有字段
      Object.keys(comp.data).forEach(k => {
        if (k !== 'genderOptions' && k !== 'raceOptions') {
          saved[k] = comp.data[k];
        }
      });
      this.setData({ __savedForm: saved });
    }

    // 切换到目标标签
    this.setData({ activeTab: to, showResult: false }, () => {
      const toId = to === 'basic' ? '#formBasic' : '#formAdvanced';
      const target = this.selectComponent(toId);
      const saved = this.data.__savedForm;
      if (target && saved) {
        // 只恢复目标表单中存在的字段
        const restore = {};
        sharedFields.forEach(k => { if (saved[k] !== undefined) restore[k] = saved[k]; });
        // 进阶字段 — 只有深度筛查有
        if (to === 'advanced') {
          Object.keys(saved).forEach(k => {
            if (!sharedFields.includes(k) && target.data[k] !== undefined) {
              restore[k] = saved[k];
            }
          });
        }
        target.setData(restore);
      }
    });

    wx.pageScrollTo({ scrollTop: 0, duration: 300 });
  },

  /** 勾选/取消免责声明 — 与倒计时互不影响 */
  toggleAgree() {
    if (this.data.canProceed) return;
    const agreed = !this.data.agreed;
    this.setData({ agreed });
    this.updateProceedState();
  },

  /** 倒计时 (页面加载时自动启动，小字显示在按钮上方) */
  startCountdown() {
    let sec = 10;
    const timer = setInterval(() => {
      sec--;
      this.setData({ countdownSec: sec });
      if (sec <= 0) {
        clearInterval(timer);
        this.setData({ countdownTimer: null, countdownDone: true });
        this.updateProceedState();
      }
    }, 1000);

    this.setData({ countdownTimer: timer });
  },

  /** 检查两个独立条件是否同时满足 */
  updateProceedState() {
    const { agreed, countdownDone } = this.data;
    if (agreed && countdownDone) {
      this.setData({ canProceed: true, btnText: '进入测试' });
    } else {
      this.setData({ btnText: '请阅读并勾选同意' });
    }
  },

  /** 关闭免责声明弹窗 */
  dismissDisclaimer() {
    if (!this.data.canProceed) return;
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer);
    }
    this.setData({ showDisclaimer: false });
  },

  /** 基础筛查提交 */
  async onBasicSubmit(e) {
    const { valid, errors, data } = validator.validateBasic(e.detail);
    if (!valid) {
      wx.showToast({ title: errors[0], icon: 'none', duration: 2500 });
      return;
    }
    this.setData({ loading: true, showResult: false });
    try {
      const result = await api.predictBasic(data);
      this.setData({ resultData: result, showResult: true, loading: false });
      wx.pageScrollTo({ selector: '#result-anchor', duration: 300 });
    } catch (err) {
      this.setData({ loading: false });
      wx.showToast({ title: err.message || '请求失败', icon: 'none', duration: 2500 });
    }
  },

  /** 深度筛查提交 */
  async onAdvancedSubmit(e) {
    const { valid, errors, data } = validator.validateAdvanced(e.detail);
    if (!valid) {
      wx.showToast({ title: errors[0], icon: 'none', duration: 2500 });
      return;
    }
    this.setData({ loading: true, showResult: false });
    try {
      const result = await api.predictAdvanced(data);
      this.setData({ resultData: result, showResult: true, loading: false });
      wx.pageScrollTo({ selector: '#result-anchor', duration: 300 });
    } catch (err) {
      this.setData({ loading: false });
      wx.showToast({ title: err.message || '请求失败', icon: 'none', duration: 2500 });
    }
  },
});

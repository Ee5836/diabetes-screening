/**
 * 深度筛查表单 (16 字段)
 */

Component({
  properties: {},

  data: {
    // 基本信息
    age: '45',
    genderIndex: 0,
    genderOptions: ['男性', '女性'],
    // 核心指标
    hba1c: '5.5',
    fastingGlucose: '5.5',
    height: '170',
    weight: '70',
    // 进阶指标 (空字符串 = 使用参考值)
    homaIr: '',
    egfr: '',
    urdact: '',
    bpSys: '',
    bpDia: '',
    triglyc: '',
    ggt: '',
    uricAcid: '',
    alt: '',
    vitD3: '',
  },

  methods: {
    onAgeInput(e) { this.setData({ age: e.detail.value }); },
    onGenderChange(e) { this.setData({ genderIndex: parseInt(e.detail.value) }); },
    onHbA1cInput(e) { this.setData({ hba1c: e.detail.value }); },
    onGlucoseInput(e) { this.setData({ fastingGlucose: e.detail.value }); },
    onHeightInput(e) { this.setData({ height: e.detail.value }); },
    onWeightInput(e) { this.setData({ weight: e.detail.value }); },
    onHomaIrInput(e) { this.setData({ homaIr: e.detail.value }); },
    onEgfrInput(e) { this.setData({ egfr: e.detail.value }); },
    onUrdactInput(e) { this.setData({ urdact: e.detail.value }); },
    onBpSysInput(e) { this.setData({ bpSys: e.detail.value }); },
    onBpDiaInput(e) { this.setData({ bpDia: e.detail.value }); },
    onTriglycInput(e) { this.setData({ triglyc: e.detail.value }); },
    onGgtInput(e) { this.setData({ ggt: e.detail.value }); },
    onUricAcidInput(e) { this.setData({ uricAcid: e.detail.value }); },
    onAltInput(e) { this.setData({ alt: e.detail.value }); },
    onVitD3Input(e) { this.setData({ vitD3: e.detail.value }); },

    handleSubmit() {
      const toNum = (v) => (v === '' ? '' : Number(v));
      const h = Number(this.data.height) || 170;
      const w = Number(this.data.weight) || 70;
      const bmi = w / ((h / 100) ** 2);

      const data = {
        age: Number(this.data.age) || 45,
        gender_adv: this.data.genderOptions[this.data.genderIndex],
        race: '非西班牙裔亚裔',
        hba1c: Number(this.data.hba1c) || 5.5,
        fasting_glucose: Number(this.data.fastingGlucose) || 5.5,
        height: h,
        weight: w,
        bmi: Math.round(bmi * 10) / 10,
        homa_ir: toNum(this.data.homaIr),
        egfr: toNum(this.data.egfr),
        urdact: toNum(this.data.urdact),
        bp_sys: toNum(this.data.bpSys),
        bp_dia: toNum(this.data.bpDia),
        triglyc: toNum(this.data.triglyc),
        ggt: toNum(this.data.ggt),
        uric_acid: toNum(this.data.uricAcid),
        alt: toNum(this.data.alt),
        vit_d3: toNum(this.data.vitD3),
      };
      this.triggerEvent('submit', data);
    },
  },
});

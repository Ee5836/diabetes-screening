/**
 * 基础筛查表单 (6 字段)
 */

Component({
  properties: {},

  data: {
    age: '45',
    genderIndex: 0,
    genderOptions: ['男性', '女性'],
    hba1c: '5.5',
    fastingGlucose: '5.5',
    height: '170',
    weight: '70',
  },

  methods: {
    onAgeInput(e) { this.setData({ age: e.detail.value }); },
    onGenderChange(e) { this.setData({ genderIndex: parseInt(e.detail.value) }); },
    onHbA1cInput(e) { this.setData({ hba1c: e.detail.value }); },
    onGlucoseInput(e) { this.setData({ fastingGlucose: e.detail.value }); },
    onHeightInput(e) { this.setData({ height: e.detail.value }); },
    onWeightInput(e) { this.setData({ weight: e.detail.value }); },

    handleSubmit() {
      const h = Number(this.data.height) || 170;
      const w = Number(this.data.weight) || 70;
      const bmi = w / ((h / 100) ** 2);

      const data = {
        age: Number(this.data.age) || 45,
        gender: this.data.genderOptions[this.data.genderIndex],
        race: '非西班牙裔亚裔',
        hba1c: Number(this.data.hba1c) || 5.5,
        fasting_glucose: Number(this.data.fastingGlucose) || 5.5,
        height: h,
        weight: w,
        bmi: Math.round(bmi * 10) / 10,
      };
      this.triggerEvent('submit', data);
    },
  },
});

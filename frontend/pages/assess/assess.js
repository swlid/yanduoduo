const api = require("../../api/index");

Page({
  data: {
    tiers: ["冲刺", "稳妥", "保底"],
    provinceOptions: [
      { name: "北京", checked: false },
      { name: "上海", checked: false },
      { name: "浙江", checked: false },
      { name: "江苏", checked: false },
      { name: "湖北", checked: false },
      { name: "陕西", checked: false }
    ],
    targetProvinces: [],
    undergradMajor: "",
    estimatedScore: "",
    isCrossMajor: false,
    degreeTypes: ["不限", "学硕", "专硕"],
    degreeIndex: 0,
    targetLevels: ["不限", "985", "211", "双一流", "普通"],
    targetLevelIndex: 0,
    submitting: false,
    result: null,
    error: ""
  },

  onUndergrad(e) {
    this.setData({ undergradMajor: e.detail.value });
  },

  onScore(e) {
    this.setData({ estimatedScore: e.detail.value });
  },

  onCross(e) {
    this.setData({ isCrossMajor: e.detail.value });
  },

  onDegree(e) {
    this.setData({ degreeIndex: Number(e.detail.value) });
  },

  onTargetLevel(e) {
    this.setData({ targetLevelIndex: Number(e.detail.value) });
  },

  onProvince(e) {
    const selected = e.detail.value || [];
    this.setData({
      targetProvinces: selected,
      provinceOptions: this.data.provinceOptions.map((item) => ({
        name: item.name,
        checked: selected.indexOf(item.name) >= 0
      }))
    });
  },

  async submit() {
    const score = Number(this.data.estimatedScore);
    if (!this.data.undergradMajor.trim()) {
      wx.showToast({ title: "请填写本科专业", icon: "none" });
      return;
    }
    if (!score || score < 0 || score > 750) {
      wx.showToast({ title: "请填写 0-750 的估分", icon: "none" });
      return;
    }

    this.setData({ submitting: true, error: "", result: null });
    try {
      const payload = {
        undergrad_major: this.data.undergradMajor.trim(),
        target_provinces: this.data.targetProvinces,
        estimated_total_score: score,
        is_cross_major: this.data.isCrossMajor,
        degree_type: this.data.degreeTypes[this.data.degreeIndex],
        target_level:
          this.data.targetLevels[this.data.targetLevelIndex] === "不限"
            ? null
            : this.data.targetLevels[this.data.targetLevelIndex]
      };
      const result = await api.createAssessment(payload);
      this.setData({ result });
    } catch (err) {
      this.setData({ error: err.message || "测评失败" });
    } finally {
      this.setData({ submitting: false });
    }
  },

  goDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}&year=2025` });
  }
});

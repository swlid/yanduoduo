const api = require("../../api/index");

Page({
  data: {
    loading: false,
    keyword: "",
    minAvg: "",
    year: 2025,
    provinceIndex: 0,
    levelIndex: 0,
    disciplineIndex: 0,
    provinces: ["全部", "北京", "上海", "浙江", "江苏", "湖北", "陕西"],
    levels: ["全部", "985", "211", "双一流", "普通"],
    disciplines: ["全部", "工学", "经济学", "教育学", "法学"],
    years: [2025, 2024, 2023],
    items: [],
    total: 0
  },

  onLoad() {
    this.loadList();
  },

  onPullDownRefresh() {
    this.loadList().finally(() => wx.stopPullDownRefresh());
  },

  onKeyword(e) {
    this.setData({ keyword: e.detail.value });
  },

  onMinAvg(e) {
    this.setData({ minAvg: e.detail.value });
  },

  onProvince(e) {
    this.setData({ provinceIndex: Number(e.detail.value) });
  },

  onLevel(e) {
    this.setData({ levelIndex: Number(e.detail.value) });
  },

  onDiscipline(e) {
    this.setData({ disciplineIndex: Number(e.detail.value) });
  },

  onYear(e) {
    const year = this.data.years[Number(e.detail.value)];
    this.setData({ year });
  },

  reset() {
    this.setData({
      keyword: "",
      minAvg: "",
      provinceIndex: 0,
      levelIndex: 0,
      disciplineIndex: 0,
      year: 2025
    });
    this.loadList();
  },

  async loadList() {
    this.setData({ loading: true });
    const params = {
      keyword: this.data.keyword || undefined,
      province: this.data.provinces[this.data.provinceIndex] === "全部"
        ? undefined
        : this.data.provinces[this.data.provinceIndex],
      level: this.data.levels[this.data.levelIndex] === "全部"
        ? undefined
        : this.data.levels[this.data.levelIndex],
      discipline_gate: this.data.disciplines[this.data.disciplineIndex] === "全部"
        ? undefined
        : this.data.disciplines[this.data.disciplineIndex],
      min_avg_score: this.data.minAvg || undefined,
      year: this.data.year,
      page: 1,
      page_size: 100
    };

    try {
      const data = await api.getInstitutionMajors(params);
      const items = (data.items || []).map((item) => {
        const difficulty = item.latest_stat && item.latest_stat.metrics
          ? item.latest_stat.metrics.difficulty
          : "未知";
        let difficultyClass = "badge-ok";
        if (difficulty === "冲刺") difficultyClass = "badge-danger";
        if (difficulty === "稳妥") difficultyClass = "badge-warn";
        return {
          ...item,
          difficultyText: difficulty || "未知",
          difficultyClass
        };
      });
      this.setData({ items, total: data.total || 0 });
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  goDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}&year=${this.data.year}`
    });
  },

  toggleCompare(e) {
    const { id } = e.currentTarget.dataset;
    const ids = wx.getStorageSync("compareIds") || [];
    const index = ids.indexOf(id);
    if (index >= 0) {
      ids.splice(index, 1);
      wx.showToast({ title: "已移出对比", icon: "none" });
    } else {
      if (ids.length >= 4) {
        wx.showToast({ title: "最多选择 4 个", icon: "none" });
        return;
      }
      ids.push(id);
      wx.showToast({ title: "已加入对比", icon: "success" });
    }
    wx.setStorageSync("compareIds", ids);
  },

  goCompare() {
    const ids = wx.getStorageSync("compareIds") || [];
    if (!ids.length) {
      wx.showToast({ title: "请先加入对比", icon: "none" });
      return;
    }
    wx.navigateTo({
      url: `/pages/compare/compare?ids=${ids.join(",")}&year=${this.data.year}`
    });
  }
});

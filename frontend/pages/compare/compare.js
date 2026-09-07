const api = require("../../api/index");

Page({
  data: {
    loading: true,
    items: [],
    year: 2025,
    rows: []
  },

  onLoad(options) {
    const year = Number(options.year || 2025);
    const ids = (options.ids || "").split(",").filter(Boolean);
    this.setData({ year });
    this.loadCompare(ids, year);
  },

  async loadCompare(ids, year) {
    if (!ids.length) {
      wx.showToast({ title: "缺少对比项", icon: "none" });
      this.setData({ loading: false });
      return;
    }
    try {
      const data = await api.compareInstitutionMajors(ids.join(","), year);
      const items = data.items || [];
      const metricDefs = [
        ["院校", (i) => i.institution.name],
        ["专业", (i) => i.major.name],
        ["层次", (i) => i.institution.level],
        ["类型", (i) => i.institution.category],
        ["地区", (i) => `${i.institution.province} ${i.institution.city}`],
        ["学硕/专硕", (i) => i.major.degree_type],
        ["学制", (i) => `${i.length || "-"} 年`],
        ["平均分", (i) => i.latest_stat && i.latest_stat.avg_score],
        ["报录比", (i) => i.latest_stat && i.latest_stat.report_rate],
        ["复录比", (i) => i.latest_stat && i.latest_stat.reexam_admit_rate],
        ["院线", (i) => i.latest_stat && i.latest_stat.college_line],
        ["难度", (i) => i.latest_stat && i.latest_stat.metrics && i.latest_stat.metrics.difficulty]
      ];
      const rows = metricDefs.map(([label, fn]) => ({
        label,
        values: items.map((item) => fn(item) ?? "-")
      }));
      this.setData({ items, rows });
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  }
});

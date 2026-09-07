const api = require("../../api/index");

Page({
  data: {
    loading: true,
    detail: null,
    year: 2025,
    statRows: []
  },

  onLoad(options) {
    this.setData({ year: Number(options.year || 2025) });
    this.loadDetail(options.id);
  },

  async loadDetail(id) {
    this.setData({ loading: true });
    try {
      const detail = await api.getInstitutionMajor(id, { year: this.data.year });
      const statRows = (detail.admission_stats || []).map((s) => ({
        year: s.year,
        plan: s.plan_total,
        applicants: s.applicant_count,
        admitted: s.admitted_count,
        reportRate: s.report_rate,
        avgScore: s.avg_score,
        collegeLine: s.college_line
      }));
      this.setData({ detail, statRows });
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  }
});

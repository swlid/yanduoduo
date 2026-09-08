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
      const fmt = (value) =>
        value === null || value === undefined || value === ""
          ? "暂无"
          : value;
      const qualityMap = {
        official: { text: "官方数据", cls: "badge-ok" },
        mock: { text: "示例数据", cls: "badge-warn" },
        none: { text: "暂无公开数据", cls: "badge-gray" },
        third_party: { text: "第三方引用", cls: "badge-warn" },
        user_submitted: { text: "用户提交", cls: "badge-gray" }
      };
      const statRows = (detail.admission_stats || []).map((s) => ({
        year: s.year,
        plan: fmt(s.plan_total),
        applicants: fmt(s.applicant_count),
        admitted: fmt(s.admitted_count),
        reportRate: fmt(s.report_rate),
        avgScore: fmt(s.avg_score),
        collegeLine: fmt(s.college_line),
        qualityText: qualityMap[s.data_quality] ? qualityMap[s.data_quality].text : s.data_quality,
        sourceName: s.source_name || "暂无",
        sourceUrl: s.source_url || "",
        updatedAt: s.updated_at ? s.updated_at.slice(0, 10) : "暂无"
      }));
      const officialCount = (detail.admission_stats || []).filter(
        (s) => s.data_quality === "official"
      ).length;
      const totalCount = (detail.admission_stats || []).length;
      const qualitySummary =
        totalCount === 0
          ? "暂无已审核招录数据"
          : officialCount === totalCount
            ? "官方已核数据"
            : officialCount === 0
              ? "示例数据（仅供演示）"
              : "示例数据与官方数据混合展示，请以各年标识为准";
      this.setData({ detail, statRows, qualitySummary });
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  }
});

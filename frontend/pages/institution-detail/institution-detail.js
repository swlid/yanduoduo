const api = require("../../api/index");

const QUALITY_MAP = {
  official: { text: "官方数据", cls: "badge-ok" },
  mock: { text: "示例数据", cls: "badge-warn" },
  none: { text: "暂无数据", cls: "badge-gray" },
  third_party: { text: "第三方引用", cls: "badge-warn" },
  user_submitted: { text: "用户提交", cls: "badge-gray" }
};

Page({
  data: {
    loading: true,
    failed: false,
    overview: null,
    regionText: "",
    yearsText: "",
    updatedText: "暂无",
    combos: [],
    comboTotal: 0,
    year: 2025,
    compareCount: 0
  },

  onLoad(options) {
    this.institutionId = options.id;
    this.loadAll();
  },

  onShow() {
    this.syncCompareCount();
  },

  onPullDownRefresh() {
    this.loadAll().finally(() => wx.stopPullDownRefresh());
  },

  syncCompareCount() {
    const ids = wx.getStorageSync("compareIds") || [];
    this.setData({ compareCount: ids.length });
  },

  async loadAll() {
    this.setData({ loading: true, failed: false });
    try {
      const overview = await api.getInstitutionOverview(this.institutionId);
      const year = overview.latest_data_year || 2025;
      const combos = await api.getInstitutionMajors({
        institution_id: this.institutionId,
        year,
        page_size: 50
      });
      const officialYears = overview.official_years || [];
      this.setData({
        overview,
        year,
        regionText:
          overview.city && overview.city !== "暂无"
            ? `${overview.province} · ${overview.city}`
            : overview.province,
        yearsText: officialYears.length
          ? `${officialYears[officialYears.length - 1]}-${officialYears[0]}`
          : "暂无",
        updatedText: overview.latest_updated_at
          ? String(overview.latest_updated_at).slice(0, 10)
          : "暂无",
        combos: (combos.items || []).map((item) => this.decorate(item)),
        comboTotal: combos.total || 0
      });
      this.syncCompareCount();
    } catch (err) {
      this.setData({ failed: true });
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  decorate(item) {
    const stat = item.latest_stat || null;
    const quality = stat
      ? QUALITY_MAP[stat.data_quality] || { text: stat.data_quality, cls: "badge-gray" }
      : { text: "该年暂无数据", cls: "badge-gray" };
    return {
      ...item,
      qualityText: quality.text,
      qualityClass: quality.cls,
      avgScore: stat && stat.avg_score !== null && stat.avg_score !== undefined ? stat.avg_score : "暂无",
      reportRate: stat && stat.report_rate !== null && stat.report_rate !== undefined ? stat.report_rate : "暂无",
      collegeLine:
        stat && stat.college_line !== null && stat.college_line !== undefined
          ? stat.college_line
          : stat && stat.self_line !== null && stat.self_line !== undefined
            ? stat.self_line
            : "暂无"
    };
  },

  goCombo(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}&year=${this.data.year}` });
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
    this.setData({ compareCount: ids.length });
  },

  goCompare() {
    const ids = wx.getStorageSync("compareIds") || [];
    if (!ids.length) {
      wx.showToast({ title: "请先加入对比", icon: "none" });
      return;
    }
    wx.navigateTo({ url: `/pages/compare/compare?ids=${ids.join(",")}&year=${this.data.year}` });
  },

  copyUrl() {
    const url = this.data.overview && this.data.overview.official_url;
    if (!url) {
      wx.showToast({ title: "暂无官方链接", icon: "none" });
      return;
    }
    wx.setClipboardData({
      data: url,
      success() {
        wx.showToast({ title: "链接已复制", icon: "success" });
      }
    });
  },

  retry() {
    this.loadAll();
  }
});

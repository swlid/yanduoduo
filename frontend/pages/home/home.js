const api = require("../../api/index");

Page({
  data: {
    loading: true,
    counts: {
      institutions: 0,
      majors: 0,
      combos: 0
    }
  },

  onLoad() {
    this.loadOverview();
  },

  onPullDownRefresh() {
    this.loadOverview().finally(() => wx.stopPullDownRefresh());
  },

  async loadOverview() {
    this.setData({ loading: true });
    try {
      const [institutions, majors, combos] = await Promise.all([
        api.getInstitutions({ page: 1, page_size: 1 }),
        api.getMajors({ page: 1, page_size: 1 }),
        api.getInstitutionMajors({ page: 1, page_size: 1, year: 2025 })
      ]);
      this.setData({
        counts: {
          institutions: institutions.total || 0,
          majors: majors.total || 0,
          combos: combos.total || 0
        }
      });
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  goInstitution() {
    wx.switchTab({ url: "/pages/institution/institution" });
  },

  goList() {
    wx.navigateTo({ url: "/pages/list/list" });
  },

  goAssess() {
    wx.navigateTo({ url: "/pages/assess/assess" });
  },

  goPlan() {
    wx.navigateTo({ url: "/pages/plan/plan" });
  },

  goCheckin() {
    wx.navigateTo({ url: "/pages/checkin/checkin" });
  },

  goTimeline() {
    wx.navigateTo({ url: "/pages/timeline/timeline" });
  }
});

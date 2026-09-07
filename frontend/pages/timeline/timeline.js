const api = require("../../api/index");

Page({
  data: {
    timeline: null,
    nodes: [],
    loading: true,
    subscribingId: ""
  },

  onLoad() {
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const [timeline, nodes] = await Promise.all([
        api.getCurrentTimeline({ today: this.today() }),
        api.getProcessNodes()
      ]);
      this.setData({ timeline, nodes });
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  today() {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${mm}-${dd}`;
  },

  async subscribe(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({ subscribingId: id });
    try {
      await api.createSubscription({
        user_id: "demo-user",
        process_node_id: id,
        advance_days: 7
      });
      wx.showToast({ title: "订阅成功", icon: "success" });
    } catch (err) {
      wx.showToast({ title: err.message || "订阅失败", icon: "none" });
    } finally {
      this.setData({ subscribingId: "" });
    }
  }
});

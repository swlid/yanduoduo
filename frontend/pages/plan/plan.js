const api = require("../../api/index");

Page({
  data: {
    subjects: ["政治", "英语", "数学", "专业课"],
    title: "",
    startDate: "2026-09-07",
    endDate: "2026-12-25",
    dailyMinutes: "360",
    targets: { 政治: "70", 英语: "65", 数学: "120", 专业课: "115" },
    currents: { 政治: "", 英语: "", 数学: "", 专业课: "" },
    loading: false,
    result: null
  },

  onTitle(e) {
    this.setData({ title: e.detail.value });
  },

  onStart(e) {
    this.setData({ startDate: e.detail.value });
  },

  onEnd(e) {
    this.setData({ endDate: e.detail.value });
  },

  onDaily(e) {
    this.setData({ dailyMinutes: e.detail.value });
  },

  onTarget(e) {
    const subject = e.currentTarget.dataset.subject;
    this.setData({ [`targets.${subject}`]: e.detail.value });
  },

  onCurrent(e) {
    const subject = e.currentTarget.dataset.subject;
    this.setData({ [`currents.${subject}`]: e.detail.value });
  },

  async submit() {
    const targets = {};
    const currents = {};
    for (const subject of ["政治", "英语", "数学", "专业课"]) {
      const target = Number(this.data.targets[subject]);
      if (!target || target <= 0) {
        wx.showToast({ title: `请填写${subject}目标分`, icon: "none" });
        return;
      }
      targets[subject] = target;
      const current = this.data.currents[subject];
      if (current !== "") {
        currents[subject] = Number(current);
      }
    }

    this.setData({ loading: true, result: null });
    try {
      const payload = {
        user_id: "demo-user",
        title: this.data.title || "考研学习计划",
        target_total_score: Object.values(targets).reduce((a, b) => a + b, 0),
        target_scores: targets,
        current_scores: currents,
        start_date: this.data.startDate,
        end_date: this.data.endDate,
        daily_minutes: Number(this.data.dailyMinutes || 360),
        reminder_time: "20:00"
      };
      const result = await api.generatePlan(payload);
      this.setData({ result });
    } catch (err) {
      wx.showToast({ title: err.message || "生成失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  goCheckin() {
    wx.navigateTo({ url: "/pages/checkin/checkin" });
  }
});

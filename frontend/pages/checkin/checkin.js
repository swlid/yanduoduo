const api = require("../../api/index");

function today() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

Page({
  data: {
    today: today(),
    subjects: ["政治", "英语", "数学", "专业课"],
    subjectIndex: 2,
    duration: "120",
    completion: "100",
    note: "",
    isMakeup: false,
    loading: false,
    progress: null
  },

  onLoad() {
    this.loadProgress();
  },

  onDate(e) {
    this.setData({ today: e.detail.value });
  },

  onSubject(e) {
    this.setData({ subjectIndex: Number(e.detail.value) });
  },

  onDuration(e) {
    this.setData({ duration: e.detail.value });
  },

  onCompletion(e) {
    this.setData({ completion: e.detail.value });
  },

  onNote(e) {
    this.setData({ note: e.detail.value });
  },

  onMakeup(e) {
    this.setData({ isMakeup: e.detail.value });
  },

  async submit() {
    const duration = Number(this.data.duration);
    if (!duration || duration <= 0) {
      wx.showToast({ title: "请填写学习时长", icon: "none" });
      return;
    }

    this.setData({ loading: true });
    try {
      await api.createCheckIn({
        user_id: "demo-user",
        date: this.data.today,
        subject: this.data.subjects[this.data.subjectIndex],
        duration_minutes: duration,
        completion: Number(this.data.completion || 100),
        note: this.data.note || null,
        is_makeup: this.data.isMakeup
      });
      wx.showToast({ title: "打卡成功", icon: "success" });
      this.setData({ note: "" });
      await this.loadProgress();
    } catch (err) {
      wx.showToast({ title: err.message || "打卡失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async loadProgress() {
    try {
      const end = today();
      const start = new Date();
      start.setDate(start.getDate() - 6);
      const mm = String(start.getMonth() + 1).padStart(2, "0");
      const dd = String(start.getDate()).padStart(2, "0");
      const startText = `${start.getFullYear()}-${mm}-${dd}`;
      const progress = await api.getProgress({
        user_id: "demo-user",
        start: startText,
        end
      });
      this.setData({ progress });
    } catch (err) {
      // 首次没有数据时不打断页面
      this.setData({ progress: null });
    }
  }
});

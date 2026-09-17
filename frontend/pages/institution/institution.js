const api = require("../../api/index");

const PAGE_SIZE = 20;
const ALL = "全部";

Page({
  data: {
    loading: false,
    loadingMore: false,
    finished: false,
    failed: false,
    keyword: "",
    total: 0,
    page: 1,
    items: [],
    provinces: [ALL],
    provinceIndex: 0,
    levels: [ALL, "985", "211", "双一流", "普通"],
    levelIndex: 0,
    sorts: ["默认排序", "有数据优先"],
    sortIndex: 0,
    onlyData: false,
    onlySelfDraw: false,
    hasDataCount: 0,
    selfDrawCount: 0
  },

  onLoad() {
    this.loadFacets().finally(() => this.loadList(true));
  },

  onPullDownRefresh() {
    this.loadList(true).finally(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    if (this.data.loading || this.data.loadingMore || this.data.finished) return;
    this.loadList(false);
  },

  async loadFacets() {
    try {
      const facets = await api.getInstitutionFacets();
      const provinces = [ALL].concat((facets.provinces || []).map((item) => item.value));
      const levels = [ALL].concat((facets.levels || []).map((item) => item.value));
      this.setData({
        provinces,
        levels,
        hasDataCount: facets.has_data_count || 0,
        selfDrawCount: facets.self_draw_count || 0
      });
    } catch (err) {
      // 分面加载失败不阻塞列表：保留默认选项
    }
  },

  onKeyword(e) {
    this.setData({ keyword: e.detail.value });
  },

  onProvince(e) {
    this.setData({ provinceIndex: Number(e.detail.value) });
    this.loadList(true);
  },

  onLevel(e) {
    this.setData({ levelIndex: Number(e.detail.value) });
    this.loadList(true);
  },

  onSort(e) {
    this.setData({ sortIndex: Number(e.detail.value) });
    this.loadList(true);
  },

  onOnlyData(e) {
    this.setData({ onlyData: e.detail.value });
    this.loadList(true);
  },

  onOnlySelfDraw(e) {
    this.setData({ onlySelfDraw: e.detail.value });
    this.loadList(true);
  },

  search() {
    this.loadList(true);
  },

  reset() {
    this.setData({
      keyword: "",
      provinceIndex: 0,
      levelIndex: 0,
      sortIndex: 0,
      onlyData: false,
      onlySelfDraw: false
    });
    this.loadList(true);
  },

  buildParams(page) {
    const { provinces, provinceIndex, levels, levelIndex, sorts, sortIndex } = this.data;
    const sortMap = ["default", "has_data"];
    const params = {
      keyword: this.data.keyword || undefined,
      province: provinces[provinceIndex] === ALL ? undefined : provinces[provinceIndex],
      level: levels[levelIndex] === ALL ? undefined : levels[levelIndex],
      is_self_draw: this.data.onlySelfDraw ? true : undefined,
      sort: sortMap[sortIndex] || "default",
      page,
      page_size: PAGE_SIZE
    };
    if (this.data.onlyData) params.has_data = true;
    return params;
  },

  decorate(item) {
    let statusText = "数据待补充";
    let statusClass = "badge-gray";
    if (item.has_official_data) {
      statusText = `官方数据 ${item.official_combo_count} 个专业`;
      statusClass = "badge-ok";
    } else if (item.combo_count > 0) {
      statusText = "示例数据（待补充）";
      statusClass = "badge-warn";
    }
    return {
      ...item,
      statusText,
      statusClass,
      regionText: item.city && item.city !== "暂无" ? `${item.province} · ${item.city}` : item.province,
      yearsText: (item.official_years || []).join("/")
    };
  },

  async loadList(reset) {
    if (reset) {
      this.setData({ loading: true, failed: false, page: 1, finished: false });
    } else {
      this.setData({ loadingMore: true });
    }
    const page = reset ? 1 : this.data.page + 1;
    try {
      const data = await api.getInstitutions(this.buildParams(page));
      const items = (data.items || []).map((item) => this.decorate(item));
      const merged = reset ? items : this.data.items.concat(items);
      this.setData({
        items: merged,
        total: data.total || 0,
        page,
        finished: merged.length >= (data.total || 0) || items.length === 0,
        failed: false
      });
    } catch (err) {
      if (reset) this.setData({ failed: true, items: [], total: 0 });
      else wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false, loadingMore: false });
    }
  },

  goDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/institution-detail/institution-detail?id=${id}` });
  },

  goComboList() {
    wx.navigateTo({ url: "/pages/list/list" });
  },

  retry() {
    this.loadList(true);
  }
});

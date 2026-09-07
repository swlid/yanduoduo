const { API_BASE } = require("../config/env");

function buildUrl(path, data) {
  const url = `${API_BASE}${path}`;
  if (!data || Object.keys(data).length === 0) return url;
  const query = Object.keys(data)
    .filter((key) => data[key] !== undefined && data[key] !== null && data[key] !== "")
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(data[key])}`)
    .join("&");
  return query ? `${url}?${query}` : url;
}

function request(method, path, data, options = {}) {
  return new Promise((resolve, reject) => {
    const isGet = method === "GET";
    wx.request({
      url: isGet ? buildUrl(path, data) : `${API_BASE}${path}`,
      method,
      data: isGet ? undefined : data,
      timeout: options.timeout || 10000,
      header: {
        "content-type": "application/json",
        ...(options.header || {})
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject({
            code: res.statusCode,
            message: (res.data && res.data.detail) || `请求失败(${res.statusCode})`
          });
        }
      },
      fail(err) {
        reject({
          code: -1,
          message: "网络连接失败，请确认后端服务已启动",
          raw: err
        });
      }
    });
  });
}

module.exports = {
  get(path, data, options) {
    return request("GET", path, data, options);
  },
  post(path, data, options) {
    return request("POST", path, data, options);
  }
};

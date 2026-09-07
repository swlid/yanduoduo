# 研多多微信小程序前端骨架

> 说明：当前本机未安装 Node.js，因此先采用**原生微信小程序**搭建前端基础，不引入 uni-app/Vite 构建链。这样可以不依赖 Node 直接导入微信开发者工具运行；后续若确需 H5 复用，再把 API 层与页面逻辑迁移到 uni-app。

## 目录结构

```text
frontend/
├─ app.js                  # 全局配置
├─ app.json                # 页面路由、窗口、tabBar
├─ app.wxss                # 全局样式
├─ project.config.json     # 微信开发者工具项目配置
├─ config/env.js           # API 地址
├─ utils/request.js        # wx.request Promise 封装
├─ api/index.js            # 业务 API 模块
└─ pages/
   ├─ home/                # 首页：概览 + 入口
   ├─ list/                # 院校专业列表 + 组合筛选
   ├─ detail/              # 院校专业详情
   └─ compare/             # 横向对比
```

## 运行前提

1. 启动后端：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. 用微信开发者工具打开 `frontend/` 目录。
3. 在开发者工具「详情 → 本地设置」勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」。
4. 后端地址默认 `http://127.0.0.1:8000/api/v1`，可在 `config/env.js` 调整。

## 已完成的地基

- 全局路由与 tabBar。
- Promise 请求封装、统一错误处理。
- 院校/专业/院校专业/对比 API 封装。
- 首页概览、列表筛选、详情、对比四个核心页面骨架。

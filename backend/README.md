# 研多多后端 MVP（里程碑 2）

本目录是 FastAPI + SQLAlchemy 后端，已实现院校/专业查询、组合筛选、详情与横向对比，并内置 Mock 数据。

## 已实现接口

- `GET /health`
- `GET /api/v1/institutions`：按关键词、地区、层次、类别、是否自划线筛选。
- `GET /api/v1/institutions/{id}`
- `GET /api/v1/majors`：按关键词、学科门类、学硕/专硕、是否接受跨考筛选。
- `GET /api/v1/majors/{id}`
- `GET /api/v1/institution-majors`：多条件组合筛选，支持地区、层次、类别、学科门类、专业、学硕/专硕、学习方式、年份、平均分区间、报录比区间。
- `GET /api/v1/institution-majors/{id}`：院校专业详情，含历年招录数据。
- `GET /api/v1/institution-majors/compare?ids=...&year=...`：最多 4 个院校专业横向对比。
- 管理后台：`POST /api/v1/admin/import`、纠错审核、资讯发布等接口。

## 本地运行（无 Docker）

默认使用 SQLite，适合快速验收。

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

首次启动会自动建表并写入 Mock 数据。打开 Swagger 文档：

<http://127.0.0.1:8000/docs>

管理后台网页：<http://127.0.0.1:8000/admin.html>

## 测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
..\.venv\Scripts\python.exe -m pytest -q
```

测试会使用独立的 `test_yanduoduo.db`，不会污染开发数据库。

## Docker 运行

```powershell
docker compose up --build
```

启动后 API 位于 <http://127.0.0.1:8000>，管理后台位于 <http://127.0.0.1:8000/admin.html>。

## 示例请求

```powershell
# 上海地区、工学、平均分不低于 340
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/institution-majors?province=上海&discipline_gate=工学&min_avg_score=340'

# 对比 3 个院校专业
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/institution-majors/compare?ids=im-001,im-008,im-010&year=2025'
```

## PostgreSQL / Redis 联调

在仓库根目录启动基础设施：

```powershell
docker compose up -d db redis
```

在 `backend/.env.example` 基础上设置环境变量：

```text
DATABASE_URL=postgresql+psycopg://yanduoduo:yanduoduo@localhost:5432/yanduoduo
REDIS_URL=redis://localhost:6379/0
```

注意：本机未安装 Docker 时，SQLite 模式仍可完整运行 API 与 Mock 数据。

## 数据说明

- 所有内置数据均为 `data_quality=mock`，仅用于功能验收，不代表真实招录事实。
- 页面/接口均带 `source_name`、`source_year`、`collected_at`、`data_quality` 字段，后续真实数据接入时沿用同一模型。

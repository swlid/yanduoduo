"""应用配置。

默认使用 SQLite，方便本地无 Docker 时直接运行 MVP；
生产/联调通过 DATABASE_URL 切换到 PostgreSQL。
"""

from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """集中管理环境变量配置。"""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "研多多 API")
        self.api_prefix: str = os.getenv("API_PREFIX", "/api/v1")

        sqlite_url = f"sqlite:///{(BASE_DIR / 'yanduoduo_dev.db').as_posix()}"
        self.database_url: str = os.getenv("DATABASE_URL", sqlite_url)
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.sql_echo: bool = os.getenv("SQL_ECHO", "0") == "1"

        cors_value = os.getenv("CORS_ORIGINS", "*")
        self.cors_origins: list[str] = [
            item.strip() for item in cors_value.split(",") if item.strip()
        ]


settings = Settings()

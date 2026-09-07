"""FastAPI 应用入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import (
    admin,
    assessments,
    content,
    institution_majors,
    institutions,
    majors,
    plans,
    study,
    timeline,
)
from .config import settings
from .db import init_db
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_if_empty()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="研多多考研全流程助手 MVP API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["系统"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(institutions.router, prefix=settings.api_prefix)
app.include_router(majors.router, prefix=settings.api_prefix)
app.include_router(institution_majors.router, prefix=settings.api_prefix)
app.include_router(assessments.router, prefix=settings.api_prefix)
app.include_router(plans.router, prefix=settings.api_prefix)
app.include_router(study.checkin_router, prefix=settings.api_prefix)
app.include_router(study.progress_router, prefix=settings.api_prefix)
app.include_router(study.report_router, prefix=settings.api_prefix)
app.include_router(timeline.router, prefix=settings.api_prefix)
app.include_router(timeline.node_router, prefix=settings.api_prefix)
app.include_router(timeline.subscription_router, prefix=settings.api_prefix)
app.include_router(content.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

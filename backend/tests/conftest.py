from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DB = Path("test_yanduoduo.db")

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SQL_ECHO"] = "0"

if TEST_DB.exists():
    TEST_DB.unlink()

from app.main import app  # noqa: E402
from app.db import engine  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def cleanup_database():
    yield
    engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()

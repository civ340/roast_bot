# 測試環境設定：在 import app 之前注入必要環境變數，並避免連線真實資料庫
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:1/test")
os.environ.setdefault("API_SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(monkeypatch):
    # request log 會寫 DB，測試中改成 no-op
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "_log_request", _noop)
    # 不使用 `with TestClient(...)`，避免觸發 lifespan 建立 DB pool
    return TestClient(main.app)

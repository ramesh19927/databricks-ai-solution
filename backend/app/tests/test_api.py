import os
import tempfile
import pathlib
import sys

# configure lightweight sqlite database for tests when Postgres is unavailable
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("USE_PGVECTOR", "false")

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.session import Base, engine


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_and_upload(client: TestClient):
    # register
    client.post(f"{settings.api_prefix}/auth/register", json={"email": "tester@example.com", "password": "testpass123"})
    login = client.post(
        f"{settings.api_prefix}/auth/login",
        data={"username": "tester@example.com", "password": "testpass123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # upload
    content = b"Hello world from unit test."
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(content)
        tmp.seek(0)
        with open(tmp.name, "rb") as f:
            files = {"file": ("sample.txt", f, "text/plain")}
            res = client.post(f"{settings.api_prefix}/documents/upload", files=files, headers=headers)
    assert res.status_code == 200

    # search
    search = client.post(
        f"{settings.api_prefix}/documents/search",
        json={"query": "Hello world", "k": 2},
        headers=headers,
    )
    assert search.status_code == 200
    assert len(search.json()) >= 1

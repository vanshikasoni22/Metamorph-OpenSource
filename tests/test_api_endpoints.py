import pytest
import httpx
from backend.app.main import app

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_api_cache.db")
    monkeypatch.setattr("backend.app.config.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.database.DATABASE_PATH", test_db)
    from backend.app.database import init_db
    init_db()

@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "service" in data

@pytest.mark.asyncio
async def test_beginner_analyze_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/beginner/analyze", json={"username": "octocat"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "octocat"
        assert len(data["recommended_issues"]) >= 2
        assert len(data["analysis_cites"]) == 4

@pytest.mark.asyncio
async def test_maintainer_fetch_malformed_url():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/maintainer/fetch", json={"issue_url": "invalid-url"})
        assert resp.status_code == 400
        assert "Malformed GitHub URL" in resp.json()["detail"]

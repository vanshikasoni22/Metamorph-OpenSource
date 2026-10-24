try:
    import pytest
except ImportError:
    class MockPytest:
        class mark:
            @staticmethod
            def asyncio(f):
                return f
        def fixture(self, *args, **kwargs):
            return lambda f: f
    pytest = MockPytest()
import httpx
from backend.app.main import app

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_api_cache.db")
    monkeypatch.setattr("backend.app.config.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.database.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.config.DATABASE_URL", f"sqlite:///{test_db}")
    monkeypatch.setattr("backend.app.database.DATABASE_URL", f"sqlite:///{test_db}")
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
async def test_html_page_routes():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Root index
        r_root = await client.get("/")
        assert r_root.status_code == 200
        assert "Contrib" in r_root.text

        # Beginner clean and html routes
        r_beg = await client.get("/beginner")
        assert r_beg.status_code == 200
        r_beg_html = await client.get("/beginner.html")
        assert r_beg_html.status_code == 200

        # Mentor clean and html routes
        r_men = await client.get("/mentor")
        assert r_men.status_code == 200
        r_men_html = await client.get("/mentor.html")
        assert r_men_html.status_code == 200

@pytest.mark.asyncio
async def test_beginner_analyze_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/beginner/analyze", json={"username": "octocat"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "octocat"
        assert len(data["recommended_issues"]) >= 2
        assert len(data["analysis_cites"]) >= 2
        assert data.get("user_profile") is not None
        assert data["user_profile"]["username"] == "octocat"
        assert "avatar_url" in data["user_profile"]

@pytest.mark.asyncio
async def test_maintainer_fetch_malformed_url():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/maintainer/fetch", json={"issue_url": "invalid-url"})
        assert resp.status_code == 400
        assert "Malformed GitHub URL" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_maintainer_history_and_persistence():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Check initial history endpoint
        r_hist = await client.get("/maintainer/history")
        assert r_hist.status_code == 200
        assert "history" in r_hist.json()

        # Score candidate PRs
        score_payload = {
            "cached": True,
            "fetched_at": "2026-10-25T02:00:00Z",
            "issue": {
                "number": 5412,
                "title": "Custom URL converters in blueprints",
                "url": "https://github.com/pallets/flask/issues/5412"
            },
            "pull_requests": [
                {
                    "number": 5415,
                    "title": "Fix blueprint converter",
                    "url": "https://github.com/pallets/flask/pull/5415",
                    "files": [],
                    "ci_status": {"total_checks": 1, "state": "success"}
                }
            ]
        }
        r_score = await client.post("/maintainer/score", json=score_payload)
        assert r_score.status_code == 200
        scored = r_score.json()
        assert len(scored["candidate_prs"]) == 1

        # Verify that score is persisted to database history
        r_hist2 = await client.get("/maintainer/history")
        assert r_hist2.status_code == 200
        items = r_hist2.json()["history"]
        assert len(items) >= 1
        assert items[0]["issue_number"] == 5412
        assert items[0]["top_score"] == 90

@pytest.mark.asyncio
async def test_beginner_save_list_and_delete():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        username = "ci_test_user"

        # 1. Save an issue
        save_payload = {
            "username": username,
            "issue": {
                "repo": "pallets/flask",
                "issue_number": 5412,
                "title": "Document custom URL converters in blueprints",
                "description": "Add docs and examples for custom URL converters.",
                "fit_score": 96,
                "estimated_hours": "1-2 hours est.",
                "implementation_steps": ["Fork repo", "Update docstring"],
                "codebase_references": []
            }
        }
        r_save = await client.post("/beginner/save", json=save_payload)
        assert r_save.status_code == 200
        assert r_save.json()["status"] == "saved"

        # 2. List saved issues
        r_list = await client.get(f"/beginner/saved?username={username}")
        assert r_list.status_code == 200
        saved_list = r_list.json()["saved_issues"]
        assert len(saved_list) == 1
        assert saved_list[0]["repo"] == "pallets/flask"
        assert saved_list[0]["issue_number"] == 5412

        # 3. Delete saved issue
        r_del = await client.delete(f"/beginner/saved/pallets/flask/5412?username={username}")
        assert r_del.status_code == 200
        assert r_del.json()["status"] == "deleted"

        # 4. Confirm it's gone
        r_list2 = await client.get(f"/beginner/saved?username={username}")
        assert len(r_list2.json()["saved_issues"]) == 0

@pytest.mark.asyncio
async def test_beginner_profile_save_and_load():
    import uuid
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        username = f"test_user_{uuid.uuid4().hex[:8]}"

        # 1. Initially profile is not found
        r_get1 = await client.get(f"/beginner/profile?username={username}")
        assert r_get1.status_code == 200
        assert r_get1.json()["status"] == "not_found"


        # 2. Save profile
        profile_data = {
            "username": username,
            "skills": [
                {"skill": "Python", "level": "beginner"},
                {"skill": "JavaScript", "level": "beginner"}
            ],
            "interests": ["cli", "developer-tools", "web"],
            "hours_per_week": 8,
            "goal": "learn",
            "growth_speed": "steady",
            "preferred_languages": ["Python", "JavaScript"],
            "difficulty_preference": "beginner"
        }
        r_save = await client.post("/beginner/profile", json=profile_data)
        assert r_save.status_code == 200
        assert r_save.json()["status"] == "saved"
        assert r_save.json()["profile"]["username"] == username
        assert len(r_save.json()["profile"]["skills"]) == 2

        # 3. Load saved profile
        r_get2 = await client.get(f"/beginner/profile?username={username}")
        assert r_get2.status_code == 200
        assert r_get2.json()["status"] == "found"
        loaded = r_get2.json()["profile"]
        assert loaded["username"] == username
        assert loaded["hours_per_week"] == 8
        assert loaded["goal"] == "learn"
        assert "cli" in loaded["interests"]


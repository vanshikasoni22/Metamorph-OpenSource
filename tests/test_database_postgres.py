try:
    import pytest
except ImportError:
    class MockPytest:
        def fixture(self, *args, **kwargs):
            return lambda f: f
        def mark(self):
            return self
    pytest = MockPytest()
import time
import json
from backend.app.database import init_db, get_cached, set_cached, delete_cached
from backend.app.services.history_service import (
    save_review_report,
    get_review_history,
    save_beginner_issue,
    get_saved_beginner_issues,
    delete_saved_beginner_issue
)
from backend.app.models import (
    MaintainerFetchResponse,
    ScoreResponse,
    IssueData,
    PRData,
    ScoredPR,
    VerdictClaim
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_postgres_layer.db")
    monkeypatch.setattr("backend.app.config.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.database.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.config.DATABASE_URL", f"sqlite:///{test_db}")
    monkeypatch.setattr("backend.app.database.DATABASE_URL", f"sqlite:///{test_db}")
    init_db()

def test_cache_operations():
    key = "test_sha256_cache_key_12345"
    payload = {"status": "ok", "items": [1, 2, 3]}

    # Set cache with 10s TTL
    set_cached(key, payload, ttl_seconds=10)

    # Get cache
    cached = get_cached(key)
    assert cached is not None
    assert cached["cached"] is True
    assert cached["status"] == "ok"
    assert cached["items"] == [1, 2, 3]

    # Delete cache
    delete_cached(key)
    assert get_cached(key) is None

def test_review_history_service():
    issue = IssueData(
        number=101,
        title="Fix race condition in connection pool",
        body="Connection pool deadlocks under concurrent requests",
        url="https://github.com/org/repo/issues/101"
    )
    pr = PRData(
        number=202,
        url="https://github.com/org/repo/pull/202",
        title="Add mutex lock to pool checkout",
        state="open"
    )
    fetch_resp = MaintainerFetchResponse(
        cached=False,
        fetched_at="2026-10-25T03:00:00Z",
        issue=issue,
        pull_requests=[pr]
    )

    scored_pr = ScoredPR(
        rank=1,
        pr_number=202,
        title=pr.title,
        author="alice",
        score=94,
        verdicts=[
            VerdictClaim(status="supported", claim="Adds mutex lock", evidence="pool.py:15")
        ],
        files=[],
        raw_pr=pr
    )
    score_resp = ScoreResponse(
        issue_title=issue.title,
        issue_number=issue.number,
        candidate_prs=[scored_pr],
        summary_markdown="PR #202 is ranked #1."
    )

    # Save review report
    report_id = save_review_report(issue.url, fetch_resp, score_resp)
    assert report_id is not None

    # Fetch history
    history = get_review_history(limit=5)
    assert len(history) >= 1
    latest = history[0]
    assert latest["issue_number"] == 101
    assert latest["top_pr_number"] == 202
    assert latest["top_score"] == 94

def test_beginner_saved_issue_service():
    username = "test_contributor"
    issue_data = {
        "repo": "pallets/flask",
        "issue_number": 5412,
        "title": "Document custom URL converters in blueprints",
        "description": "Add documentation for custom converters.",
        "fit_score": 98,
        "estimated_hours": "1-3 hours est.",
        "url": "https://github.com/pallets/flask/issues/5412",
        "implementation_steps": ["Step 1", "Step 2"],
        "codebase_references": [{"type": "repo", "reference": "https://github.com/pallets/flask"}]
    }

    # Save
    success = save_beginner_issue(issue_data, saved_by=username)
    assert success is True

    # Retrieve
    saved = get_saved_beginner_issues(saved_by=username)
    assert len(saved) == 1
    assert saved[0]["repo"] == "pallets/flask"
    assert saved[0]["issue_number"] == 5412
    assert len(saved[0]["implementation_steps"]) == 2

    # Delete
    deleted = delete_saved_beginner_issue("pallets/flask", 5412, saved_by=username)
    assert deleted is True

    # Verify empty
    assert len(get_saved_beginner_issues(saved_by=username)) == 0

import os
import pytest
import httpx
import json
import time
from backend.app.services.github_client import (
    parse_github_url,
    GitHubClient,
    GitHubClientError,
    RateLimitExceededError,
    ResourceNotFoundError
)
from backend.app.services.cache_service import (
    generate_cache_key,
    get_maintainer_cache,
    set_maintainer_cache,
    invalidate_maintainer_cache
)
from backend.app.database import init_db

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_cache.db")
    monkeypatch.setattr("backend.app.config.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.database.DATABASE_PATH", test_db)
    init_db()

# 1. URL Parsing Tests
def test_parse_github_url_valid():
    owner, repo, number, url_type = parse_github_url("https://github.com/pallets/flask/issues/5412")
    assert owner == "pallets"
    assert repo == "flask"
    assert number == 5412
    assert url_type == "issues"

    owner, repo, number, url_type = parse_github_url("https://github.com/pallets/flask/pull/5415#discussion_r123")
    assert owner == "pallets"
    assert repo == "flask"
    assert number == 5415
    assert url_type == "pull"

def test_parse_github_url_malformed():
    with pytest.raises(GitHubClientError) as exc_info:
        parse_github_url("not-a-valid-url")
    assert "Malformed GitHub URL" in str(exc_info.value)

    with pytest.raises(GitHubClientError) as exc_info:
        parse_github_url("https://github.com/pallets/flask/issues/not-a-number")
    assert "Malformed GitHub URL" in str(exc_info.value)

def test_parse_github_url_expected_type():
    with pytest.raises(GitHubClientError) as exc_info:
        parse_github_url("https://github.com/pallets/flask/issues/5412", expected_type="pull")
    assert "expected pull" in str(exc_info.value)

# 2. Pagination & Missing Patch Tests
@pytest.mark.asyncio
async def test_pagination_and_missing_patch():
    # Mock transport to simulate paginated responses and missing patch
    def handler(request: httpx.Request):
        url = str(request.url)
        page = request.url.params.get("page", "1")
        if "/pulls/101/files" in url:
            if page == "1":
                # Page 1 returns 100 items (first has patch, second has omitted patch)
                files = [{"filename": f"file_{i}.py", "status": "modified", "additions": 1, "deletions": 0, "patch": "@@ +1 @@"} for i in range(100)]
                files[1]["patch"] = None  # Omitted patch
                files[2]["patch"] = ""    # Empty string patch
                return httpx.Response(200, json=files)
            elif page == "2":
                # Page 2 returns 5 items
                files = [{"filename": f"page2_file_{i}.py", "status": "added", "additions": 5, "deletions": 0, "patch": "@@ -0,0 +1,5 @@"} for i in range(5)]
                return httpx.Response(200, json=files)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        gh = GitHubClient(token=None, http_client=client)
        files = await gh.fetch_pr_files(client, "owner", "repo", 101)

        assert len(files) == 105
        # Verify patch omission handling
        assert files[0].patch == "@@ +1 @@"
        assert files[1].patch == "unknown"  # Critical requirement: None becomes 'unknown'
        assert files[2].patch == "unknown"  # Empty string becomes 'unknown'

# 3. 404 Error Handling Test
@pytest.mark.asyncio
async def test_404_resource_not_found():
    def handler(request: httpx.Request):
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        gh = GitHubClient(token=None, http_client=client)
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await gh.fetch_issue(client, "owner", "repo", 999999)
        assert "not found" in str(exc_info.value).lower()

# 4. Rate Limit Handling Test
@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    reset_ts = int(time.time()) + 3600
    def handler(request: httpx.Request):
        return httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset_ts)},
            json={"message": "API rate limit exceeded"}
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        gh = GitHubClient(token=None, http_client=client)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await gh.fetch_issue(client, "owner", "repo", 123)
        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in str(exc_info.value).lower()

# 5. Cache Hit & Force Refresh Tests
def test_cache_hit_and_ttl():
    issue_url = "https://github.com/owner/repo/issues/1"
    pr_urls = ["https://github.com/owner/repo/pull/10"]
    data = {"issue": {"number": 1, "title": "Test Issue"}, "pull_requests": []}

    # Initial state: Cache miss
    assert get_maintainer_cache(issue_url, pr_urls) is None

    # Store with TTL
    set_maintainer_cache(issue_url, data, pr_urls=pr_urls, ttl_seconds=60)

    # Cache hit
    cached = get_maintainer_cache(issue_url, pr_urls)
    assert cached is not None
    assert cached["cached"] is True
    assert cached["issue"]["title"] == "Test Issue"

    # Invalidate / force refresh
    invalidate_maintainer_cache(issue_url, pr_urls)
    assert get_maintainer_cache(issue_url, pr_urls) is None

# 6. Non-fatal single PR failure test
@pytest.mark.asyncio
async def test_one_failing_pr_does_not_fail_request():
    def handler(request: httpx.Request):
        url = str(request.url)
        if "/issues/1" in url:
            return httpx.Response(200, json={"number": 1, "title": "Main Issue", "state": "open", "labels": [], "assignees": [], "user": {"login": "alice"}, "html_url": "https://github.com/owner/repo/issues/1"})
        elif "/pulls/10" in url:
            # PR 10 succeeds
            return httpx.Response(200, json={"number": 10, "title": "Good PR", "state": "open", "user": {"login": "bob"}, "head": {"sha": "abc"}, "html_url": "https://github.com/owner/repo/pull/10"})
        elif "/pulls/10/files" in url:
            return httpx.Response(200, json=[])
        elif "/check-runs" in url or "/status" in url:
            return httpx.Response(200, json={"check_runs": []})
        elif "/pulls/20" in url:
            # PR 20 returns 404
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        gh = GitHubClient(token=None, http_client=client)
        resp = await gh.fetch_maintainer_data(
            issue_url="https://github.com/owner/repo/issues/1",
            pr_urls=["https://github.com/owner/repo/pull/10", "https://github.com/owner/repo/pull/20"]
        )

        assert resp.issue.number == 1
        assert len(resp.pull_requests) == 2
        # PR 10 is successful
        pr10 = next(p for p in resp.pull_requests if p.number == 10)
        assert pr10.error is None
        assert pr10.title == "Good PR"
        # PR 20 failed gracefully
        pr20 = next(p for p in resp.pull_requests if p.number == 20)
        assert pr20.error is not None
        assert "not found" in pr20.error.lower()

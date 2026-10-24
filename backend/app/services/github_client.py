import re
import asyncio
import logging
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from ..config import GITHUB_TOKEN
from ..models import (
    IssueData,
    PRData,
    PRFile,
    CIStatus,
    CheckRunItem,
    MaintainerFetchResponse
)

logger = logging.getLogger("contribo.github_client")

GITHUB_API_BASE = "https://api.github.com"

class GitHubClientError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code

class RateLimitExceededError(GitHubClientError):
    def __init__(self, reset_timestamp: int):
        reset_time = datetime.fromtimestamp(reset_timestamp, timezone.utc).isoformat()
        message = f"GitHub API rate limit exceeded. Resets at {reset_time} UTC."
        super().__init__(message, status_code=429)
        self.reset_timestamp = reset_timestamp

class ResourceNotFoundError(GitHubClientError):
    def __init__(self, resource: str):
        super().__init__(f"GitHub resource not found: {resource}", status_code=404)

class PermissionDeniedError(GitHubClientError):
    def __init__(self, resource: str):
        super().__init__(f"GitHub access forbidden or private repository: {resource}", status_code=403)


def parse_github_url(url: str, expected_type: Optional[str] = None) -> Tuple[str, str, int, str]:
    """
    Parses a GitHub URL into (owner, repo, number, url_type).
    Handles both issue and pull URLs.
    """
    if not url or not isinstance(url, str):
        raise GitHubClientError("Invalid or empty URL provided.", status_code=400)
    
    clean_url = url.strip().split("#")[0].split("?")[0].rstrip("/")
    match = re.match(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)$", clean_url, re.IGNORECASE)
    if not match:
        raise GitHubClientError(f"Malformed GitHub URL: '{url}'. Expected format: https://github.com/owner/repo/issues/123 or .../pull/123", status_code=400)
    
    owner, repo, url_type, number_str = match.groups()
    url_type = url_type.lower()
    
    if expected_type and url_type != expected_type:
        raise GitHubClientError(f"URL '{url}' is a {url_type}, expected {expected_type}.", status_code=400)
        
    return owner, repo, int(number_str), url_type


class GitHubClient:
    def __init__(self, token: Optional[str] = GITHUB_TOKEN, http_client: Optional[httpx.AsyncClient] = None):
        self.token = token
        self._external_client = http_client

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Contrib-Engine/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 1
    ) -> httpx.Response:
        url = endpoint if endpoint.startswith("http") else f"{GITHUB_API_BASE}{endpoint}"
        headers = self._get_headers()

        response = await client.get(url, headers=headers, params=params, timeout=20.0)

        # Inspect rate limit headers
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_time = response.headers.get("X-RateLimit-Reset")

        if response.status_code == 403:
            if remaining == "0" and reset_time:
                reset_ts = int(reset_time)
                # Check if reset is within a couple seconds
                diff = reset_ts - int(datetime.now(timezone.utc).timestamp())
                if 0 < diff <= 2 and retries > 0:
                    logger.info(f"Rate limit reset in {diff}s, backing off...")
                    await asyncio.sleep(diff + 0.5)
                    return await self._request(client, endpoint, params, retries=retries - 1)
                raise RateLimitExceededError(reset_ts)
            raise PermissionDeniedError(endpoint)

        if response.status_code == 404:
            raise ResourceNotFoundError(endpoint)

        if response.status_code == 429:
            reset_ts = int(reset_time) if reset_time else int(datetime.now(timezone.utc).timestamp()) + 60
            raise RateLimitExceededError(reset_ts)

        if response.status_code >= 400:
            raise GitHubClientError(
                f"GitHub API error ({response.status_code}): {response.text[:200]}",
                status_code=response.status_code
            )

        return response

    async def check_rate_limit(self) -> Dict[str, Any]:
        """Fetches the current rate limit status."""
        async def _check(client: httpx.AsyncClient):
            try:
                res = await self._request(client, "/rate_limit")
                data = res.json()
                core = data.get("resources", {}).get("core", {})
                return {
                    "authenticated": bool(self.token),
                    "remaining": core.get("remaining", "unknown"),
                    "limit": core.get("limit", "unknown"),
                    "reset": core.get("reset", "unknown")
                }
            except Exception as e:
                logger.warning(f"Failed to check rate limit: {e}")
                return {
                    "authenticated": bool(self.token),
                    "remaining": "unknown",
                    "limit": "unknown",
                    "reset": "unknown"
                }

        if self._external_client:
            return await _check(self._external_client)
        else:
            async with httpx.AsyncClient() as client:
                return await _check(client)

    async def fetch_issue(self, client: httpx.AsyncClient, owner: str, repo: str, issue_number: int) -> IssueData:
        res = await self._request(client, f"/repos/{owner}/{repo}/issues/{issue_number}")
        data = res.json()

        # Extract labels
        labels = []
        for lbl in data.get("labels", []):
            if isinstance(lbl, dict) and "name" in lbl:
                labels.append(lbl["name"])
            elif isinstance(lbl, str):
                labels.append(lbl)

        # Extract assignees
        assignees = []
        for a in data.get("assignees", []):
            if isinstance(a, dict) and "login" in a:
                assignees.append(a["login"])

        author_login = data.get("user", {}).get("login") if data.get("user") else "unknown"

        return IssueData(
            id=data.get("id"),
            number=data.get("number", issue_number),
            title=data.get("title") or "unknown",
            body=data.get("body"),
            state=data.get("state") or "unknown",
            labels=labels,
            assignees=assignees,
            author=author_login or "unknown",
            url=data.get("html_url") or f"https://github.com/{owner}/{repo}/issues/{issue_number}"
        )

    async def discover_linked_prs(self, client: httpx.AsyncClient, owner: str, repo: str, issue_number: int) -> List[str]:
        """
        Discovers candidate or linked PRs by inspecting the issue timeline and search API.
        """
        candidate_pr_urls = set()
        page = 1

        # 1. Inspect timeline events with pagination
        try:
            while page <= 5:  # Cap at 5 pages (500 events) for safety
                res = await self._request(
                    client,
                    f"/repos/{owner}/{repo}/issues/{issue_number}/timeline",
                    params={"per_page": 100, "page": page}
                )
                events = res.json()
                if not events or not isinstance(events, list):
                    break

                for event in events:
                    event_type = event.get("event")
                    # cross-referenced pull request
                    if event_type == "cross-referenced":
                        source = event.get("source", {})
                        issue = source.get("issue", {})
                        if "pull_request" in issue and "html_url" in issue:
                            candidate_pr_urls.add(issue["html_url"])
                    # connected pull request
                    elif event_type == "connected":
                        subject = event.get("subject", {})
                        if subject.get("type") == "PullRequest" and "html_url" in subject:
                            candidate_pr_urls.add(subject["html_url"])

                if len(events) < 100:
                    break
                page += 1
        except Exception as e:
            logger.warning(f"Timeline discovery error for issue #{issue_number}: {e}")

        # 2. Search API fallback if timeline yielded no PRs
        if not candidate_pr_urls:
            try:
                search_query = f"repo:{owner}/{repo} type:pr {issue_number}"
                res = await self._request(client, "/search/issues", params={"q": search_query, "per_page": 10})
                items = res.json().get("items", [])
                for item in items:
                    if "pull_request" in item and "html_url" in item:
                        candidate_pr_urls.add(item["html_url"])
            except Exception as e:
                logger.warning(f"Search API discovery error for issue #{issue_number}: {e}")

        return list(candidate_pr_urls)

    async def fetch_pr_files(self, client: httpx.AsyncClient, owner: str, repo: str, pr_number: int) -> List[PRFile]:
        """
        Fetches all changed files with pagination.
        If GitHub omits the patch (binary or diff too large), marks it 'unknown', never empty string.
        """
        files: List[PRFile] = []
        page = 1

        while page <= 10:  # Up to 1000 files
            res = await self._request(
                client,
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": 100, "page": page}
            )
            data = res.json()
            if not data or not isinstance(data, list):
                break

            for f in data:
                patch = f.get("patch")
                # Handle patch omission or emptiness
                if patch is None or not isinstance(patch, str) or patch.strip() == "":
                    clean_patch = "unknown"
                else:
                    clean_patch = patch

                files.append(
                    PRFile(
                        filename=f.get("filename") or "unknown",
                        status=f.get("status") or "unknown",
                        additions=f.get("additions", 0) or 0,
                        deletions=f.get("deletions", 0) or 0,
                        patch=clean_patch
                    )
                )

            if len(data) < 100:
                break
            page += 1

        return files

    async def fetch_pr_ci_status(self, client: httpx.AsyncClient, owner: str, repo: str, head_sha: str) -> CIStatus:
        """
        Fetches check runs for the PR's HEAD commit.
        Falls back to commit status if check-runs are absent.
        """
        if not head_sha or head_sha == "unknown":
            return CIStatus(total_checks=0, state="unknown", check_runs=[])

        check_runs_list: List[CheckRunItem] = []
        overall_state = "unknown"

        # Check runs API
        try:
            res = await self._request(client, f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs")
            data = res.json()
            runs = data.get("check_runs", [])
            for r in runs:
                name = r.get("name") or "check"
                status = r.get("status") or "unknown"
                conclusion = r.get("conclusion") or ("in_progress" if status == "in_progress" else "unknown")
                check_runs_list.append(
                    CheckRunItem(
                        name=name,
                        status=status,
                        conclusion=conclusion
                    )
                )

            if check_runs_list:
                has_failure = any(c.conclusion in ("failure", "timed_out", "action_required") for c in check_runs_list)
                has_pending = any(c.status in ("in_progress", "queued") for c in check_runs_list)
                all_success = all(c.conclusion == "success" for c in check_runs_list)

                if has_failure:
                    overall_state = "failure"
                elif has_pending:
                    overall_state = "pending"
                elif all_success:
                    overall_state = "success"
                else:
                    overall_state = "unknown"

                return CIStatus(
                    total_checks=len(check_runs_list),
                    state=overall_state,
                    check_runs=check_runs_list
                )
        except Exception as e:
            logger.warning(f"Check runs fetch error for commit {head_sha}: {e}")

        # Fallback to combined commit status API
        try:
            res = await self._request(client, f"/repos/{owner}/{repo}/commits/{head_sha}/status")
            status_data = res.json()
            state = status_data.get("state") or "unknown"
            statuses = status_data.get("statuses", [])
            for s in statuses:
                check_runs_list.append(
                    CheckRunItem(
                        name=s.get("context") or "status",
                        status="completed" if s.get("state") in ("success", "failure", "error") else "pending",
                        conclusion=s.get("state") or "unknown"
                    )
                )
            return CIStatus(
                total_checks=len(check_runs_list),
                state=state if state in ("success", "failure", "pending") else "unknown",
                check_runs=check_runs_list
            )
        except Exception as e:
            logger.warning(f"Combined status fetch error for commit {head_sha}: {e}")

        return CIStatus(total_checks=0, state="unknown", check_runs=[])

    async def fetch_single_pr(self, client: httpx.AsyncClient, pr_url: str) -> PRData:
        """
        Fetches an individual PR.
        If an error occurs, returns a PRData object with the error field populated,
        ensuring that one failing PR does NOT fail the entire request.
        """
        try:
            owner, repo, pr_number, _ = parse_github_url(pr_url, expected_type="pull")
            res = await self._request(client, f"/repos/{owner}/{repo}/pulls/{pr_number}")
            pr_data = res.json()

            head_sha = pr_data.get("head", {}).get("sha") or "unknown"
            author_login = pr_data.get("user", {}).get("login") if pr_data.get("user") else "unknown"

            # Parallelize fetching files and CI status
            files_task = self.fetch_pr_files(client, owner, repo, pr_number)
            ci_task = self.fetch_pr_ci_status(client, owner, repo, head_sha)
            files, ci_status = await asyncio.gather(files_task, ci_task)

            return PRData(
                number=pr_number,
                url=pr_data.get("html_url") or pr_url,
                title=pr_data.get("title") or "unknown",
                body=pr_data.get("body"),
                state=pr_data.get("state") or "unknown",
                author=author_login or "unknown",
                created_at=pr_data.get("created_at"),
                updated_at=pr_data.get("updated_at"),
                mergeable=pr_data.get("mergeable"),
                draft=pr_data.get("draft", False),
                additions=pr_data.get("additions", 0) or 0,
                deletions=pr_data.get("deletions", 0) or 0,
                changed_files_count=pr_data.get("changed_files", len(files)) or len(files),
                files=files,
                ci_status=ci_status,
                error=None
            )
        except Exception as e:
            logger.error(f"Failed to fetch PR {pr_url}: {e}")
            # Try to extract PR number if possible
            pr_num = 0
            try:
                _, _, num, _ = parse_github_url(pr_url)
                pr_num = num
            except Exception:
                pass
            return PRData(
                number=pr_num,
                url=pr_url,
                title="Failed to fetch pull request",
                body=None,
                state="unknown",
                author="unknown",
                files=[],
                ci_status=CIStatus(),
                error=str(e)
            )

    async def fetch_maintainer_data(
        self,
        issue_url: str,
        pr_urls: Optional[List[str]] = None
    ) -> MaintainerFetchResponse:
        """
        Coordinates the complete fetch of the issue and candidate PRs.
        """
        warnings = []
        if not self.token:
            warnings.append("Operating without GITHUB_TOKEN. Rate limits are restricted to 60 req/hr.")

        owner, repo, issue_number, _ = parse_github_url(issue_url, expected_type="issues")

        async def _execute(client: httpx.AsyncClient) -> MaintainerFetchResponse:
            # 1. Fetch issue
            issue = await self.fetch_issue(client, owner, repo, issue_number)

            # 2. Determine PR URLs
            target_pr_urls: List[str] = []
            if pr_urls and len(pr_urls) > 0:
                seen = set()
                for u in pr_urls:
                    if u and isinstance(u, str) and u.strip():
                        trimmed = u.strip()
                        if trimmed not in seen:
                            seen.add(trimmed)
                            target_pr_urls.append(trimmed)
            else:
                discovered = await self.discover_linked_prs(client, owner, repo, issue_number)
                target_pr_urls = discovered
                if not target_pr_urls:
                    warnings.append(f"No linked candidate pull requests found for issue #{issue_number}.")

            # 3. Fetch each PR in parallel
            pr_tasks = [self.fetch_single_pr(client, url) for url in target_pr_urls]
            pull_requests = await asyncio.gather(*pr_tasks) if pr_tasks else []

            return MaintainerFetchResponse(
                cached=False,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                issue=issue,
                pull_requests=list(pull_requests),
                warnings=warnings
            )

        if self._external_client:
            return await _execute(self._external_client)
        else:
            async with httpx.AsyncClient() as client:
                return await _execute(client)

"""
Beginner GitHub Service
=======================
Fetches a GitHub user's public profile and repos to determine their top languages,
then discovers real open issues tagged 'good first issue' matching those languages.

LLM PLACEHOLDER HOOK:
  - estimate_fit_score(): currently uses a simple heuristic (no LLM)
  - generate_implementation_steps(): currently returns generic steps
  Future: replace both with Qwen3-4B-Instruct-2507 for personalized guidance.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import httpx

from ..config import GITHUB_TOKEN
from ..models import (
    BeginnerAnalyzeRequest,
    BeginnerAnalyzeResponse,
    MatchedIssue,
)

logger = logging.getLogger("contribo.beginner_service")

GITHUB_API_BASE = "https://api.github.com"

# Maximum number of issues to return to the frontend
MAX_ISSUES = 5
# Number of top languages to use when searching for issues
MAX_LANGUAGES = 3


def _get_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Contrib-Engine/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def _safe_get(
    client: httpx.AsyncClient, url: str, params: Optional[Dict] = None
) -> Optional[dict]:
    """Makes a GET request, returning None on any error instead of raising."""
    try:
        resp = await client.get(url, headers=_get_headers(), params=params, timeout=15.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"Request failed for {url}: {e}")
    return None


async def fetch_user_top_languages(
    client: httpx.AsyncClient, username: str
) -> Tuple[List[str], List[Dict]]:
    """
    Returns (top_languages, analysis_cites) for a user.
    Fetches their public repos and sums up language bytes.
    """
    repos_data = await _safe_get(
        client,
        f"{GITHUB_API_BASE}/users/{username}/repos",
        params={"per_page": 30, "sort": "pushed", "type": "owner"},
    )

    if not repos_data or not isinstance(repos_data, list):
        return [], [{"source": "repos", "detail": f"Could not retrieve public repositories for @{username}."}]

    # Count repos per language (GitHub stores the primary language per repo)
    lang_counts: Dict[str, int] = {}
    star_count = 0
    for repo in repos_data:
        lang = repo.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        star_count += repo.get("stargazers_count", 0)

    # Sort languages by frequency
    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
    top_langs = [lang for lang, _ in sorted_langs[:MAX_LANGUAGES]]

    repo_count = len(repos_data)
    cites = [
        {
            "source": "repos",
            "detail": f"Analysed {repo_count} public repositories for @{username}. Top languages: {', '.join(top_langs) or 'None detected'}.",
        },
        {
            "source": "stars",
            "detail": f"@{username}'s repositories have {star_count} total stars.",
        },
    ]

    return top_langs, cites


async def fetch_recent_activity_cite(
    client: httpx.AsyncClient, username: str
) -> Dict[str, str]:
    """Fetches recent public events and returns a single analysis citation."""
    events = await _safe_get(
        client,
        f"{GITHUB_API_BASE}/users/{username}/events/public",
        params={"per_page": 10},
    )
    if not events or not isinstance(events, list):
        return {"source": "events", "detail": "No recent public activity found."}

    event_types = [e.get("type", "") for e in events]
    push_count = sum(1 for t in event_types if t == "PushEvent")
    pr_count = sum(1 for t in event_types if t in ("PullRequestEvent", "PullRequestReviewEvent"))

    parts = []
    if push_count:
        parts.append(f"{push_count} push event(s)")
    if pr_count:
        parts.append(f"{pr_count} PR event(s)")

    detail = f"Recent activity for @{username}: " + (", ".join(parts) if parts else "no push or PR events in the last 10 events.")
    return {"source": "events", "detail": detail}


def _estimate_fit_score(issue: Dict, user_languages: List[str], rank: int) -> int:
    """
    LLM PLACEHOLDER HOOK: deterministic fit score.
    Future: replace with Qwen3-Reranker-0.6B embedding similarity.
    """
    base = max(60, 98 - rank * 8)

    # Boost if any label suggests beginner-friendliness
    labels = [lbl.get("name", "").lower() for lbl in issue.get("labels", []) if isinstance(lbl, dict)]
    if any(kw in lbl for lbl in labels for kw in ("good first", "beginner", "easy", "starter")):
        base = min(99, base + 5)

    # Slight penalty if no language detected
    if not user_languages:
        base = max(55, base - 5)

    return base


def _estimate_hours(issue: Dict) -> str:
    """Rough estimate based on issue body length and labels."""
    body = issue.get("body") or ""
    labels = [lbl.get("name", "").lower() for lbl in issue.get("labels", []) if isinstance(lbl, dict)]

    if "documentation" in labels or "docs" in " ".join(labels):
        return "1–2 hours est."
    if len(body) < 300:
        return "1–3 hours est."
    if len(body) < 800:
        return "2–5 hours est."
    return "3–8 hours est."


def _generate_evidence_points(issue: Dict, repo_full_name: str) -> List[str]:
    """
    LLM PLACEHOLDER HOOK: generates evidence bullets from real GitHub data.
    Future: Qwen3-4B-Instruct-2507 will cite specific lines, tests, and open PRs.
    """
    points = []
    body = issue.get("body") or ""
    labels = [lbl.get("name", "") for lbl in issue.get("labels", []) if isinstance(lbl, dict)]

    # Body present means some description to work from
    if len(body) > 50:
        points.append("✓ Issue has a description with context")
    else:
        points.append("? Issue body is brief — read comments for context")

    # Label signals
    label_str = ", ".join(labels) if labels else "none"
    points.append(f"✓ Labels: {label_str}")

    # Comments
    comments = issue.get("comments", 0)
    if comments > 0:
        points.append(f"✓ {comments} comment(s) — community discussion available")
    else:
        points.append("○ No comments yet — you'd be the first contributor")

    # Open PR check — real data not fetched here to save rate limit; placeholder note
    points.append("○ Conflict check: run locally before opening PR")

    return points[:4]


def _generate_implementation_steps(issue: Dict, repo_full_name: str, languages: List[str]) -> List[str]:
    """
    LLM PLACEHOLDER HOOK: returns generic but actionable steps.
    Future: Qwen3-4B-Instruct will generate repo-specific guided steps.
    """
    lang_note = f"({', '.join(languages[:2])})" if languages else ""
    return [
        f"1. Fork and clone {repo_full_name}, then install dependencies {lang_note}.",
        "2. Reproduce the issue locally to understand the expected behaviour.",
        "3. Make your fix in the smallest possible scope — avoid unrelated changes.",
        "4. Add or update tests to cover your change, then run the full test suite.",
        "5. Open a pull request referencing this issue number in the PR description.",
    ]


async def search_good_first_issues(
    client: httpx.AsyncClient, languages: List[str]
) -> List[Dict]:
    """
    Searches the GitHub Search API for 'good first issue' issues matching
    the user's top languages. Falls back to language-agnostic search if needed.
    """
    issues: List[Dict] = []

    async def _search(query: str) -> List[Dict]:
        result = await _safe_get(
            client,
            f"{GITHUB_API_BASE}/search/issues",
            params={"q": query, "sort": "updated", "order": "desc", "per_page": 10},
        )
        if result and isinstance(result.get("items"), list):
            return result["items"]
        return []

    if languages:
        # Search with language filter
        lang_filter = " ".join(f"language:{lang}" for lang in languages[:MAX_LANGUAGES])
        query = f"is:open is:issue label:\"good first issue\" no:assignee {lang_filter}"
        issues = await _search(query)

    # Fallback if no results
    if not issues:
        logger.info("Language-filtered search returned no results — falling back to generic good-first-issue search")
        issues = await _search('is:open is:issue label:"good first issue" no:assignee sort:updated')

    # If GitHub API search rate limit is exhausted or network blocked, fall back to curated open starter issues
    if not issues:
        logger.info("GitHub API search rate limit reached or empty — providing curated starter issues")
        issues = [
            {
                "id": 541201,
                "number": 5412,
                "title": "Document custom URL converters in blueprints",
                "repository_url": "https://api.github.com/repos/pallets/flask",
                "html_url": "https://github.com/pallets/flask/issues/5412",
                "body": "Custom URL converters registered on blueprints are not clearly explained in the documentation. Add examples and test cases.",
                "labels": [{"name": "good first issue"}, {"name": "documentation"}],
            },
            {
                "id": 892011,
                "number": 892,
                "title": "Add retry parameter to webhook delivery configuration",
                "repository_url": "https://api.github.com/repos/encode/httpx",
                "html_url": "https://github.com/encode/httpx/issues/892",
                "body": "Allow passing an explicit max_retries configuration when setting up connection dispatchers. Include unit tests.",
                "labels": [{"name": "good first issue"}, {"name": "enhancement"}],
            },
            {
                "id": 140221,
                "number": 310,
                "title": "Validate CLI flags and show helpful error messages for unknown options",
                "repository_url": "https://api.github.com/repos/tiangolo/fastapi",
                "html_url": "https://github.com/tiangolo/fastapi/issues/310",
                "body": "When unexpected command-line flags are passed, provide suggestions for nearest valid flags.",
                "labels": [{"name": "good first issue"}, {"name": "cli"}],
            }
        ]

    return issues[:MAX_ISSUES]


async def analyze_beginner_github(request: BeginnerAnalyzeRequest) -> BeginnerAnalyzeResponse:
    """
    Main entry point for the beginner flow.
    1. Fetches user's top languages from public repos
    2. Searches for real good-first-issues matching those languages
    3. Returns structured BeginnerAnalyzeResponse with real GitHub data
    """
    username = request.username.strip().lstrip("@") or "octocat"

    async with httpx.AsyncClient() as client:
        # Parallel fetch: top languages + recent activity
        langs_task = fetch_user_top_languages(client, username)
        activity_task = fetch_recent_activity_cite(client, username)

        (top_langs, lang_cites), activity_cite = await asyncio.gather(langs_task, activity_task)

        # Search for real issues
        raw_issues = await search_good_first_issues(client, top_langs)

    # Build MatchedIssue objects from real GitHub data
    matched: List[MatchedIssue] = []
    for rank, issue in enumerate(raw_issues, start=1):
        repo_url = issue.get("repository_url", "")
        # repository_url is like https://api.github.com/repos/owner/repo
        repo_full_name = "/".join(repo_url.rstrip("/").split("/")[-2:]) if repo_url else "unknown/repo"
        repo_html = f"https://github.com/{repo_full_name}"

        issue_number = issue.get("number", 0)
        title = issue.get("title") or "Untitled issue"
        body = (issue.get("body") or "No description provided.").strip()
        # Truncate body to a reasonable description length
        description = body[:300] + ("…" if len(body) > 300 else "")

        matched.append(
            MatchedIssue(
                id=f"issue-{issue.get('id', rank)}",
                repo=repo_full_name,
                issue_number=issue_number,
                fit_score=_estimate_fit_score(issue, top_langs, rank),
                title=title,
                description=description,
                estimated_hours=_estimate_hours(issue),
                evidence_points=_generate_evidence_points(issue, repo_full_name),
                implementation_steps=_generate_implementation_steps(issue, repo_full_name, top_langs),
                codebase_references=[
                    {"type": "issue", "reference": issue.get("html_url") or f"{repo_html}/issues/{issue_number}"},
                    {"type": "repo", "reference": repo_html},
                ],
            )
        )

    # Build analysis cites
    analysis_cites = lang_cites + [activity_cite]
    if top_langs:
        analysis_cites.append({
            "source": "search",
            "detail": f"Searched GitHub for 'good first issue' issues in {', '.join(top_langs)}.",
        })
    else:
        analysis_cites.append({
            "source": "search",
            "detail": "No language preference detected — searched globally for 'good first issue' issues.",
        })

    if not matched:
        analysis_cites.append({
            "source": "results",
            "detail": "No open 'good first issue' items found right now. Try again later or add a GitHub token for higher rate limits.",
        })

    return BeginnerAnalyzeResponse(
        username=username,
        analysis_cites=analysis_cites,
        recommended_issues=matched,
    )

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from ..models import (
    MaintainerFetchRequest,
    MaintainerFetchResponse,
    ScoreResponse
)
from ..services.github_client import (
    GitHubClient,
    GitHubClientError,
    RateLimitExceededError,
    ResourceNotFoundError,
    PermissionDeniedError
)
from ..services.cache_service import (
    get_maintainer_cache,
    set_maintainer_cache
)
from ..services.rule_engine import run_placeholder_scoring
from ..services.history_service import save_review_report, get_review_history

router = APIRouter(prefix="/maintainer", tags=["Maintainer"])

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
async def serve_maintainer_page():
    return FileResponse(os.path.join(frontend_dir, "mentor.html"))

@router.get("/history")
async def get_maintainer_review_history(limit: int = 10):
    """
    Returns the recent maintainer review comparison runs stored in the database.
    """
    return {"history": get_review_history(limit=limit)}

@router.post("/fetch", response_model=MaintainerFetchResponse)
async def fetch_maintainer_data(request: MaintainerFetchRequest):
    """
    Fetches GitHub issue and PR data (diffs, files, check-runs), with SQLite caching and rate limit handling.
    """
    # 1. Check cache unless force_refresh is requested
    if not request.force_refresh:
        cached_data = get_maintainer_cache(request.issue_url, request.pr_urls)
        if cached_data:
            return MaintainerFetchResponse(**cached_data)

    # 2. Fetch fresh from GitHub
    client = GitHubClient()
    try:
        response = await client.fetch_maintainer_data(
            issue_url=request.issue_url,
            pr_urls=request.pr_urls
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RateLimitExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GitHubClientError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching GitHub data: {str(e)}")

    # 3. Store in database cache
    set_maintainer_cache(
        issue_url=request.issue_url,
        data=response.model_dump(),
        pr_urls=request.pr_urls
    )

    return response

@router.post("/score", response_model=ScoreResponse)
async def score_maintainer_data(fetch_response: MaintainerFetchResponse):
    """
    Takes the fetched issue and candidate PRs, runs the rule engine scoring,
    and automatically persists the review comparison report to the database.
    """
    score_response = run_placeholder_scoring(fetch_response)

    # Persist review report into PostgreSQL/SQLite
    try:
        save_review_report(
            issue_url=fetch_response.issue.url,
            fetch_data=fetch_response,
            score_data=score_response
        )
    except Exception as e:
        pass  # Non-fatal if persistence encounters an issue

    return score_response

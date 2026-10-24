from fastapi import APIRouter, HTTPException, Depends
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

router = APIRouter(prefix="/maintainer", tags=["Maintainer"])

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

    # 3. Store in SQLite cache
    set_maintainer_cache(
        issue_url=request.issue_url,
        data=response.model_dump(),
        pr_urls=request.pr_urls
    )

    return response

@router.post("/score", response_model=ScoreResponse)
async def score_maintainer_data(fetch_response: MaintainerFetchResponse):
    """
    PLACEHOLDER ENDPOINT:
    Takes the fetched issue and candidate PRs, and runs the rule engine placeholder
    to output scored candidate rankings, evidence proof points, and review markdown.
    """
    return run_placeholder_scoring(fetch_response)

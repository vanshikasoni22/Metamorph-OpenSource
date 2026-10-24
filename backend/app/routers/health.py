from fastapi import APIRouter
from ..services.github_client import GitHubClient

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    client = GitHubClient()
    rate_info = await client.check_rate_limit()
    return {
        "status": "healthy",
        "service": "Contrib Evidence Engine",
        "authenticated": rate_info.get("authenticated", False),
        "rate_limit_remaining": rate_info.get("remaining"),
        "rate_limit_limit": rate_info.get("limit"),
        "rate_limit_reset": rate_info.get("reset")
    }

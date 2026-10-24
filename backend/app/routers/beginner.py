from fastapi import APIRouter, HTTPException
from ..models import (
    BeginnerAnalyzeRequest,
    BeginnerAnalyzeResponse,
)
from ..services.beginner_service import analyze_beginner_github

router = APIRouter(prefix="/beginner", tags=["Beginner"])

@router.post("/analyze", response_model=BeginnerAnalyzeResponse)
async def analyze_beginner_profile(request: BeginnerAnalyzeRequest):
    """
    Fetches a GitHub user's public repositories to detect their top languages,
    then searches for real open 'good first issue' issues matching those languages.

    LLM PLACEHOLDER HOOK: Fit scoring and implementation steps are currently
    deterministic heuristics. Future integration: Qwen3-4B-Instruct-2507 for
    personalized guidance and Qwen3-Reranker-0.6B for issue ranking.
    """
    try:
        return await analyze_beginner_github(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze GitHub profile for '{request.username}': {str(e)}"
        )

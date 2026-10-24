import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..models import (
    BeginnerAnalyzeRequest,
    BeginnerAnalyzeResponse,
    BeginnerProfileInput,
)
from ..services.beginner_service import analyze_beginner_github
from ..services.history_service import (
    save_beginner_issue,
    get_saved_beginner_issues,
    delete_saved_beginner_issue,
    save_user_profile,
    get_user_profile
)

from pydantic import BaseModel
from typing import Optional, Dict, Any

class SaveIssueRequest(BaseModel):
    issue: Dict[str, Any]
    username: Optional[str] = "anonymous"

router = APIRouter(prefix="/beginner", tags=["Beginner"])

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
async def serve_beginner_page():
    return FileResponse(os.path.join(frontend_dir, "beginner.html"))

@router.get("/saved")
async def list_saved_issues(username: str = "anonymous"):
    """
    Returns bookmarked issues saved by a contributor.
    """
    return {"saved_issues": get_saved_beginner_issues(saved_by=username)}

@router.post("/save")
async def bookmark_issue(req: SaveIssueRequest):
    """
    Saves / bookmarks an issue into the database.
    """
    success = save_beginner_issue(req.issue, saved_by=req.username or "anonymous")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save issue to database.")
    return {"status": "saved", "repo": req.issue.get("repo"), "issue_number": req.issue.get("issue_number")}

@router.delete("/saved/{repo:path}/{issue_number}")
async def remove_saved_issue(repo: str, issue_number: int, username: str = "anonymous"):
    """
    Deletes a saved issue from bookmarks.
    """
    delete_saved_beginner_issue(repo=repo, issue_number=issue_number, saved_by=username)
    return {"status": "deleted"}

@router.post("/analyze", response_model=BeginnerAnalyzeResponse)
async def analyze_beginner_profile(request: BeginnerAnalyzeRequest):
    """
    Fetches a GitHub user's public repositories to detect their top languages,
    then searches for real open 'good first issue' issues matching those languages.
    """
    try:
        return await analyze_beginner_github(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze GitHub profile for '{request.username}': {str(e)}"
        )

@router.get("/profile")
async def get_profile(username: str):
    """
    Loads saved beginner questionnaire profile for a user.
    """
    profile = get_user_profile(username)
    if profile:
        return {"status": "found", "profile": profile}
    return {"status": "not_found", "profile": None}

@router.post("/profile")
async def save_profile(profile_input: BeginnerProfileInput):
    """
    Saves or updates beginner questionnaire profile in the database.
    """
    profile_dict = profile_input.model_dump()
    saved = save_user_profile(profile_dict)
    if not saved:
        raise HTTPException(status_code=500, detail="Could not save profile to database.")
    return {"status": "saved", "profile": profile_dict}


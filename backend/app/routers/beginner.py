import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from ..models import (
    BeginnerAnalyzeRequest,
    BeginnerAnalyzeResponse,
    BeginnerProfileInput,
    PlanRequest,
    BeginnerPlan,
    PlanTask,
    TaskPatchRequest,
    TaskPatchResponse,
)
from ..services.beginner_service import analyze_beginner_github
from ..services.plan_service import generate_beginner_plan
from ..services.llm_client import LLMPaymentRequiredError, LLMError
from ..services.history_service import (
    save_beginner_issue,
    get_saved_beginner_issues,
    delete_saved_beginner_issue,
    save_user_profile,
    get_user_profile,
    update_beginner_task,
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


@router.post("/plan", response_model=BeginnerPlan)
async def create_beginner_plan(request: PlanRequest):
    """
    Generates a personalised task plan (CG-01, CG-02, CG-03) for a beginner
    who has selected an issue.
    """
    try:
        return await generate_beginner_plan(request=request)
    except LLMPaymentRequiredError as e:
        raise HTTPException(
            status_code=402,
            detail=f"AI provider billing or credit limit reached: {str(e)}"
        )
    except LLMError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Plan unavailable, please try again: {str(e)}"
        )
    except Exception as e:
        logger.exception("Unexpected error in plan generation")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating the plan: {str(e)}"
        )


@router.patch("/tasks/{task_id}", response_model=TaskPatchResponse)
async def patch_beginner_task(task_id: str, request: TaskPatchRequest):
    """
    Rule 1: Updates task_status and optional blocker_note of a single task.
    Rejects any request that attempts to set verification_status.
    """
    if request.verification_status is not None:
        raise HTTPException(
            status_code=400,
            detail="verification_status cannot be modified by the user; it is set only by the system upon verification"
        )

    allowed_statuses = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETED"}
    if request.task_status is not None and request.task_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task_status '{request.task_status}'. Allowed values: {', '.join(sorted(allowed_statuses))}"
        )

    result = update_beginner_task(
        username=request.username,
        issue_url=request.issue_url,
        task_id=task_id,
        task_status=request.task_status,
        blocker_note=request.blocker_note,
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found for user '{request.username}' and issue '{request.issue_url}'"
        )

    return TaskPatchResponse(
        status="ok",
        task=PlanTask(**result["task"]),
        completed_count=result["completed_count"],
        verified_count=result["verified_count"],
        total_tasks=result["total_tasks"],
    )


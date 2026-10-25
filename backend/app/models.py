from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class CheckRunItem(BaseModel):
    name: str
    status: str
    conclusion: Optional[str] = "unknown"

class CIStatus(BaseModel):
    total_checks: int = 0
    state: str = "unknown"  # success, failure, pending, unknown
    check_runs: List[CheckRunItem] = Field(default_factory=list)

class PRFile(BaseModel):
    filename: str
    status: str = "unknown"
    additions: int = 0
    deletions: int = 0
    patch: str = "unknown"  # Critical: never empty; if omitted by GitHub or binary, "unknown"

class PRData(BaseModel):
    number: int
    url: str
    title: str
    body: Optional[str] = None
    state: str = "unknown"
    author: Optional[str] = "unknown"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    mergeable: Optional[bool] = None
    draft: Optional[bool] = None
    additions: Optional[int] = 0
    deletions: Optional[int] = 0
    changed_files_count: Optional[int] = 0
    files: List[PRFile] = Field(default_factory=list)
    ci_status: CIStatus = Field(default_factory=CIStatus)
    error: Optional[str] = None  # Non-fatal error if this single PR failed

class IssueData(BaseModel):
    id: Optional[int] = None
    number: int
    title: str
    body: Optional[str] = None
    state: str = "unknown"
    labels: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    author: Optional[str] = "unknown"
    url: str

class MaintainerFetchRequest(BaseModel):
    issue_url: str
    pr_urls: Optional[List[str]] = Field(default_factory=list)
    force_refresh: Optional[bool] = False

class MaintainerFetchResponse(BaseModel):
    cached: bool = False
    fetched_at: str
    issue: IssueData
    pull_requests: List[PRData] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

# Models for Placeholder scoring and Beginner flow
class VerdictClaim(BaseModel):
    status: str  # supported, unknown, blocker
    claim: str
    evidence: str

class ScoredPR(BaseModel):
    rank: int
    pr_number: int
    title: str
    author: str
    score: int
    verdicts: List[VerdictClaim]
    files: List[PRFile]
    raw_pr: PRData

class ScoreResponse(BaseModel):
    issue_title: str
    issue_number: int
    candidate_prs: List[ScoredPR]
    summary_markdown: str

class UserProfileData(BaseModel):
    username: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    total_stars: int = 0
    top_languages: List[str] = Field(default_factory=list)
    html_url: Optional[str] = None

class BeginnerAnalyzeRequest(BaseModel):
    username: str

class MatchedIssue(BaseModel):
    id: str
    repo: str
    issue_number: int
    fit_score: int
    title: str
    description: str
    estimated_hours: str
    evidence_points: List[str] = Field(default_factory=list)
    implementation_steps: List[str] = Field(default_factory=list)
    codebase_references: List[Dict[str, str]] = Field(default_factory=list)
    html_url: Optional[str] = None

class BeginnerAnalyzeResponse(BaseModel):
    username: str
    user_profile: Optional[UserProfileData] = None
    analysis_cites: List[Dict[str, str]] = Field(default_factory=list)
    recommended_issues: List[MatchedIssue] = Field(default_factory=list)

class SkillItem(BaseModel):
    skill: str
    level: str = Field(default="beginner", description="beginner, intermediate, advanced")

class BeginnerProfileInput(BaseModel):
    username: str
    skills: List[SkillItem] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    hours_per_week: int = Field(default=8, ge=1, le=100)
    goal: str = Field(default="learn", description="learn, resume, GSoC, give_back")
    growth_speed: str = Field(default="steady", description="casual, steady, fast")
    preferred_languages: List[str] = Field(default_factory=list)
    difficulty_preference: str = Field(default="beginner", description="beginner, intermediate, challenging")

class BeginnerProfileResponse(BaseModel):
    status: str = "ok"
    profile: BeginnerProfileInput
    updated_at: Optional[str] = None


# ─────────────────────────────────────────────────────────────────
# Phase 4 — Beginner Plan & Task Models (CG-01 / CG-02 / CG-03)
# ─────────────────────────────────────────────────────────────────

class PlanTask(BaseModel):
    """A single concrete task derived from an issue requirement."""
    task_id: str = Field(description="Code-generated stable ID, e.g. 'T-01'")
    requirement_id: Optional[str] = Field(default=None, description="Linked requirement ID from Phase 2 (e.g. 'R1'). None for template tasks.")
    category: str = Field(description="One of: understand, set_up, investigate, plan, implement, test, submit")
    title: str
    purpose: str = Field(description="'Why this matters' — one line")
    steps: List[str] = Field(default_factory=list, description="Concrete sub-steps")
    relevant_files: List[str] = Field(default_factory=list, description="File paths from repo evidence. 'unknown' if not supported by evidence.")
    learning_objective: Optional[str] = None
    estimated_time: str = Field(default="unknown", description="Time range estimate, e.g. '1–2 hours (est.)'")
    completion_criteria: str = Field(default="", description="How to know this task is done")
    verification_method: Optional[str] = Field(default="unknown", description="Verification command from README/CONTRIBUTING or 'unknown'")
    is_template: bool = Field(default=False, description="True if this task was added from a fixed template, not from Qwen analysis")
    task_status: str = Field(default="NOT_STARTED", description="User-reported: NOT_STARTED, IN_PROGRESS, BLOCKED, COMPLETED")
    verification_status: str = Field(default="NOT_CHECKED", description="System-verified: NOT_CHECKED, VERIFIED, FAILED, UNVERIFIED")
    blocker_note: Optional[str] = Field(default=None, description="Optional note if task_status is BLOCKED")
    prerequisites: List[str] = Field(default_factory=list, description="Task prerequisites")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs this task depends on")
    week_number: int = Field(default=1, description="Assigned week in the weekly schedule")
    part_label: Optional[str] = Field(default=None, description="E.g. 'Part 1 of 2' if split across weeks")


class WeeklyScheduleItem(BaseModel):
    """Weekly breakdown scaled to contributor's hours per week and growth speed."""
    week_number: int
    planned_hours: float
    target_hours: float
    hours_label: str = Field(description="e.g. 'Planned for 4.5 of your 6 hours'")
    task_ids: List[str] = Field(default_factory=list)
    focus_summary: str = ""


class QwenPlanOutput(BaseModel):
    """Schema sent to Qwen for structured plan generation. Task IDs are NOT generated by Qwen."""
    tasks: List[Dict[str, Any]] = Field(description="List of task objects. Do NOT include task_id — it will be assigned by the system.")
    first_approach_note: str = Field(default="", description="Short 'your first approach' note built only from issue and repo facts")


class BeginnerPlan(BaseModel):
    """The full personalised plan returned to the beginner."""
    status: str = "ok"
    analysis_type: str = "beginner_plan_cg01_cg02_cg03"
    issue_number: int
    issue_url: str
    issue_title: str
    tasks: List[PlanTask] = Field(default_factory=list)
    weekly_schedule: List[WeeklyScheduleItem] = Field(default_factory=list)
    first_approach_note: str = ""
    profile_summary: str = ""
    requirement_ids_used: List[str] = Field(default_factory=list, description="Requirement IDs the plan was built from")
    model_logged: str = ""
    generated_at: str = ""
    warnings: List[str] = Field(default_factory=list)
    completed_count: int = 0
    verified_count: int = 0
    total_tasks: int = 0
    note: str = "This plan is a suggestion based on available evidence. A human makes the final decisions."


class PlanRequest(BaseModel):
    username: str
    issue_url: str
    requirement_list: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Optional requirement list from Phase 2. If absent, will attempt to extract."
    )
    regenerate: bool = Field(
        default=False,
        description="If True, regenerates the plan and resets task progress. If False, returns existing plan if already saved."
    )


class TaskPatchRequest(BaseModel):
    username: str
    issue_url: str
    task_status: Optional[str] = None
    blocker_note: Optional[str] = None
    verification_status: Optional[str] = None  # Must NOT be modified by user; rejected if provided


class TaskPatchResponse(BaseModel):
    status: str = "ok"
    task: PlanTask
    completed_count: int
    verified_count: int
    total_tasks: int


class PlanErrorResponse(BaseModel):
    status: str = "error"
    error: str
    error_type: str = Field(default="plan_unavailable", description="plan_unavailable, provider_billing, validation_error")
    detail: Optional[str] = None

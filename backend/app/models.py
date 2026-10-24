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
    evidence_points: List[str]
    implementation_steps: List[str]
    codebase_references: List[Dict[str, str]]

class BeginnerAnalyzeResponse(BaseModel):
    username: str
    analysis_cites: List[Dict[str, str]]
    recommended_issues: List[MatchedIssue]

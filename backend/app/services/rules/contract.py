from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from ...models import IssueData, PRData

class RuleStatus(str, Enum):
    # Legacy statuses (existing rules)
    PASS = "pass"
    FAIL = "fail"
    SUPPORTED = "supported"
    BLOCKER = "blocker"
    UNKNOWN = "unknown"
    # PV spec-aligned statuses
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    CONCERN = "concern"
    NOT_EVALUATED = "not_evaluated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CRITICAL_FLAG = "critical_flag"  # Failing CI visible flag (not a rejection)

class EvidenceItem(BaseModel):
    source: str = Field(description="Origin of evidence e.g. 'diff', 'ci_check', 'issue_body', 'file'")
    reference: Optional[str] = Field(default=None, description="Exact reference e.g. 'src/app.py:12-25' or 'check_run/lint'")
    detail: str = Field(description="Descriptive finding or snippet")
    status: Optional[str] = Field(default=None, description="Status of this individual evidence item if applicable")

class RuleResultMetadata(BaseModel):
    rule_version: str = "1.0.0"
    model_id: Optional[str] = None
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_type: str = "deterministic"  # "deterministic", "llm", "hybrid"

class RuleResult(BaseModel):
    rule_id: str
    status: RuleStatus
    score: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Optional numerical score (0-100 or 0.0-1.0)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidential confidence between 0.0 and 1.0")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Citations and evidence points")
    recommended_action: str = Field(description="Clear next step for the maintainer or contributor")
    metadata: RuleResultMetadata = Field(default_factory=RuleResultMetadata)

class RuleContext(BaseModel):
    issue: Optional[IssueData] = None
    pr: Optional[PRData] = None
    all_prs: Optional[List[PRData]] = Field(default_factory=list)
    user_skills: Optional[List[str]] = Field(default_factory=list)
    user_interests: Optional[List[str]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)

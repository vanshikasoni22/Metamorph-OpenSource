"""
PV Engine — Sub-step A plain-logic orchestrator
------------------------------------------------
Builds one RuleContext per candidate PR (issue + current PR + sibling PRs)
and runs all four PV plain-logic rules via the shared RuleRunner.

Returns a PVPlainLogicReport containing per-PR rule results.
Sub-step A only — no AI involvement.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .rules.contract import RuleResult, RuleContext
from .rules.runner import RuleRunner
from .rules.pv import (
    TestPresenceRule,
    CIStatusRule,
    DuplicateOverlapRule,
    ScopePassRule,
)
from ..models import IssueData, PRData, MaintainerFetchResponse
from ..config import QWEN_MODEL

logger = logging.getLogger("contribo.pv_engine")

# --------------------------------------------------------------------------- #
# Output models                                                                #
# --------------------------------------------------------------------------- #

class PRRuleReport(BaseModel):
    pr_number: int
    pr_url: str
    pr_title: str
    pr_author: str
    rule_results: List[RuleResult]


class PVPlainLogicReport(BaseModel):
    """
    Sub-step A plain-logic results.
    Labelled explicitly: no AI, no requirement coverage — deterministic rules only.
    """
    analysis_type: str = "sub_step_a_plain_logic"
    description: str = (
        "Plain-logic (deterministic) rule results only. "
        "No AI or requirement coverage analysis is included. "
        "These results are a precursor to Sub-step B (Qwen requirement coverage)."
    )
    rule_version: str = "1.1.0"
    model_logged: str = Field(
        default_factory=lambda: QWEN_MODEL or "none (sub-step A uses no AI)"
    )
    analyzed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    issue_number: int
    issue_url: str
    issue_title: str
    pr_reports: List[PRRuleReport]
    warnings: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Runner setup (singleton-style; instantiated at module import)                #
# --------------------------------------------------------------------------- #

_runner = RuleRunner()
_runner.register(TestPresenceRule())
_runner.register(CIStatusRule())
_runner.register(DuplicateOverlapRule())
_runner.register(ScopePassRule())

_PV_RULE_IDS = ["PV-04", "PV-05", "PV-08", "PV-SCOPE"]


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

async def run_plain_logic_analysis(
    fetch_response: MaintainerFetchResponse,
    extra: Optional[dict] = None,
) -> PVPlainLogicReport:
    """
    Run the four Sub-step A plain-logic rules against every candidate PR
    in the MaintainerFetchResponse.

    Each PR's context includes the full sibling list so PV-08 (overlap)
    can compare across PRs.
    """
    issue    = fetch_response.issue
    all_prs  = fetch_response.pull_requests or []
    warnings = list(fetch_response.warnings or [])
    pr_reports: List[PRRuleReport] = []

    if not all_prs:
        warnings.append("No candidate PRs available for analysis.")

    for pr in all_prs:
        context = RuleContext(
            issue=issue,
            pr=pr,
            all_prs=all_prs,          # siblings include self; rules filter by pr.number
            extra=extra or {},
        )

        try:
            results = await _runner.run_all(context, rule_ids=_PV_RULE_IDS)
        except Exception as exc:
            logger.exception(f"Rule runner failed for PR #{pr.number}: {exc}")
            results = []
            warnings.append(f"Rule runner error for PR #{pr.number}: {exc}")

        pr_reports.append(PRRuleReport(
            pr_number=pr.number,
            pr_url=pr.url,
            pr_title=pr.title,
            pr_author=pr.author or "unknown",
            rule_results=results,
        ))

    return PVPlainLogicReport(
        issue_number=issue.number,
        issue_url=issue.url,
        issue_title=issue.title,
        pr_reports=pr_reports,
        warnings=warnings,
    )

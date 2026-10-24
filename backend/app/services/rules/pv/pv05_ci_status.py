"""
PV-05 CI Status
---------------
Plain-logic rule (no AI). Reads pre-fetched CIStatus (check-runs or
combined commit status) and maps conclusions to spec-aligned statuses.

NEVER executes any code from the PR. Reads only the already-fetched
check-run conclusion values from the GitHub Checks API.

Status vocabulary:
  satisfied             – all checks completed with "success" conclusion
  partially_satisfied   – some checks pass, none explicitly failed (e.g. skipped/neutral)
  concern               – one or more checks are still pending / queued
  critical_flag         – one or more checks concluded with failure/timed_out/action_required
                          (visible flag; does NOT auto-reject the PR)
  not_evaluated         – no CI checks configured for this PR
  insufficient_evidence – head SHA missing or CI data could not be fetched

Confidence:
  1.0 when check data is present
  0.5 when data was absent and a fallback was used
  0.0 when head SHA is missing
"""

from typing import List

from ..base import BaseRule
from ..contract import RuleContext, RuleResult, RuleStatus, EvidenceItem

_FAILING_CONCLUSIONS = {"failure", "timed_out", "action_required", "cancelled"}
_SUCCESS_CONCLUSIONS = {"success", "neutral", "skipped"}
_PENDING_STATUSES   = {"in_progress", "queued", "pending", "waiting", "requested"}


class CIStatusRule(BaseRule):
    """
    PV-05: CI Status
    Reads check-run conclusions already fetched from GitHub. Never executes code.
    Failing CI is surfaced as a visible critical_flag, not an auto-rejection.
    """

    rule_id = "PV-05"
    rule_name = "CI Status"
    rule_type = "deterministic"
    version = "1.1.0"

    async def evaluate(self, context: RuleContext) -> RuleResult:
        if not context or not context.pr:
            return self._missing("PRData object")

        pr = context.pr
        ci = pr.ci_status

        if not ci:
            return self._missing("CIStatus (not present in PRData)")

        # No checks configured at all
        if ci.total_checks == 0:
            return self.build_result(
                status=RuleStatus.NOT_EVALUATED,
                score=None,
                confidence=0.5,
                evidence=[EvidenceItem(
                    source="ci",
                    reference=f"PR #{pr.number}",
                    detail="No CI checks were found for this PR's HEAD commit. Repository may not have CI configured.",
                    status="not_evaluated"
                )],
                recommended_action=(
                    "No CI checks found. Consider configuring automated checks "
                    "to validate code quality and correctness."
                )
            )

        evidence: List[EvidenceItem] = []
        failing, pending, passing, other = [], [], [], []

        for run in ci.check_runs:
            conclusion = (run.conclusion or "").lower()
            status     = (run.status or "").lower()
            name       = run.name or "check"
            ref        = f"check/{name}"

            if conclusion in _FAILING_CONCLUSIONS:
                failing.append(name)
                evidence.append(EvidenceItem(
                    source="ci_check",
                    reference=ref,
                    detail=f"Check '{name}' concluded: {conclusion} (status: {status})",
                    status="critical_flag"
                ))
            elif status in _PENDING_STATUSES or conclusion in ("", None):
                pending.append(name)
                evidence.append(EvidenceItem(
                    source="ci_check",
                    reference=ref,
                    detail=f"Check '{name}' is still in progress (status: {status}, conclusion: {conclusion or 'none yet'})",
                    status="concern"
                ))
            elif conclusion in _SUCCESS_CONCLUSIONS:
                passing.append(name)
                evidence.append(EvidenceItem(
                    source="ci_check",
                    reference=ref,
                    detail=f"Check '{name}' passed (conclusion: {conclusion})",
                    status="satisfied"
                ))
            else:
                other.append(name)
                evidence.append(EvidenceItem(
                    source="ci_check",
                    reference=ref,
                    detail=f"Check '{name}' has unrecognised conclusion: {conclusion!r} (status: {status})",
                    status="insufficient_evidence"
                ))

        total = len(ci.check_runs)

        # --- CRITICAL FLAG: any failures ---
        if failing:
            evidence.insert(0, EvidenceItem(
                source="ci_summary",
                reference=f"PR #{pr.number}",
                detail=(
                    f"⚠ CRITICAL FLAG — {len(failing)}/{total} check(s) failed: "
                    f"{', '.join(failing)}. This is a visible flag only. A human maintainer makes the final decision."
                ),
                status="critical_flag"
            ))
            return self.build_result(
                status=RuleStatus.CRITICAL_FLAG,
                score=0.0,
                confidence=1.0,
                evidence=evidence,
                recommended_action=(
                    f"Review failing check(s): {', '.join(failing)}. "
                    "Ask contributor to address these before the maintainer makes a merge decision. "
                    "This is a recommendation only — the maintainer decides."
                )
            )

        # --- CONCERN: checks still pending ---
        if pending:
            return self.build_result(
                status=RuleStatus.CONCERN,
                score=None,
                confidence=0.7,
                evidence=evidence,
                recommended_action=(
                    f"{len(pending)}/{total} check(s) are still in progress: {', '.join(pending)}. "
                    "Wait for all checks to complete before making a merge decision."
                )
            )

        # --- SATISFIED: all pass (success / neutral / skipped) ---
        if passing and not other:
            return self.build_result(
                status=RuleStatus.SATISFIED,
                score=100.0,
                confidence=1.0,
                evidence=evidence,
                recommended_action=(
                    f"All {total} CI check(s) passed. Review check details before merging."
                )
            )

        # --- PARTIALLY SATISFIED: some pass, some unrecognised ---
        return self.build_result(
            status=RuleStatus.PARTIALLY_SATISFIED,
            score=round(100.0 * len(passing) / total, 1) if total else None,
            confidence=0.8,
            evidence=evidence,
            recommended_action=(
                f"{len(passing)}/{total} check(s) passed; {len(other)} had unrecognised conclusions. "
                "Inspect check details before merging."
            )
        )

    def _missing(self, desc: str) -> RuleResult:
        return self.build_result(
            status=RuleStatus.INSUFFICIENT_EVIDENCE,
            score=None,
            confidence=0.0,
            evidence=[EvidenceItem(
                source="system",
                reference="input_validation",
                detail=f"Missing or insufficient data: {desc}",
                status="insufficient_evidence"
            )],
            recommended_action=f"Provide {desc} to evaluate PV-05."
        )

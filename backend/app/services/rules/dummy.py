from .base import BaseRule
from .contract import RuleContext, RuleResult, RuleStatus, EvidenceItem

class DummyCheckRule(BaseRule):
    """
    DM-01 Dummy Rule: Verifies that an issue title has sufficient descriptive length (>= 5 chars).
    Used to validate the rule lifecycle, Section 2 contract, and missing-data fallbacks.
    """
    rule_id = "DM-01"
    rule_type = "deterministic"
    version = "1.0.0"

    async def evaluate(self, context: RuleContext) -> RuleResult:
        if not context or not context.issue:
            return self.handle_missing_data(
                missing_desc="IssueData object",
                recommended_action="Provide a valid issue with title and number to evaluate DM-01."
            )

        issue = context.issue
        title = (issue.title or "").strip()

        if not title:
            return self.handle_missing_data(
                missing_desc="Issue title is empty or blank",
                recommended_action="Add a descriptive title to the issue."
            )

        if len(title) < 5:
            return self.build_result(
                status=RuleStatus.FAIL,
                score=0.2,
                confidence=1.0,
                evidence=[
                    EvidenceItem(
                        source="issue_title",
                        reference=f"issue:{issue.number}",
                        detail=f"Issue title '{title}' is only {len(title)} characters (minimum 5 required).",
                        status="fail"
                    )
                ],
                recommended_action="Expand issue title to clearly summarize the problem."
            )

        return self.build_result(
            status=RuleStatus.PASS,
            score=1.0,
            confidence=1.0,
            evidence=[
                EvidenceItem(
                    source="issue_title",
                    reference=f"issue:{issue.number}",
                    detail=f"Issue title has valid length ({len(title)} chars): '{title[:40]}...'",
                    status="pass"
                )
            ],
            recommended_action="Issue title satisfies basic descriptive requirements."
        )

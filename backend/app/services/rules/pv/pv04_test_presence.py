"""
PV-04 Test Presence
-------------------
Plain-logic rule (no AI). Inspects PR file list to determine whether
test coverage was added or maintained.

Status vocabulary (spec-aligned):
  satisfied             – test files added or meaningfully expanded
  partially_satisfied   – existing test files touched but additions ≤ deletions
  concern               – no test files touched (and PR is not docs-only)
  not_evaluated         – docs-only PR; rule not applicable
  insufficient_evidence – no file data available

Confidence:
  1.0 when file data is present and unambiguous
  0.5 when only partial file data is available (some patches unknown)
"""

import re
from typing import List

from ..base import BaseRule
from ..contract import RuleContext, RuleResult, RuleStatus, EvidenceItem

# Patterns that identify test files
_TEST_FILE_RE = re.compile(
    r"(^|/)(test[s]?[_/]|[_/]?test[s]?\.(py|js|ts|go|java|rb|rs|cpp|cs)|"
    r"spec[s]?[_/]|[_/]?spec\.(py|js|ts|go)|"
    r"__tests__/)",
    re.IGNORECASE,
)

# Patterns that identify documentation-only files
_DOCS_FILE_RE = re.compile(
    r"\.(md|rst|txt|adoc|docx?|pdf|html|htm|svg|png|jpg|gif|ico|lock|toml"
    r"|yaml|yml|json|xml|csv|tsv|ini|cfg|conf|env\.example)$",
    re.IGNORECASE,
)


def _is_test_file(filename: str) -> bool:
    return bool(_TEST_FILE_RE.search(filename))


def _is_docs_file(filename: str) -> bool:
    return bool(_DOCS_FILE_RE.search(filename))


class TestPresenceRule(BaseRule):
    """
    PV-04: Test Presence
    Checks whether the PR adds or maintains test coverage.
    Exempts documentation-only PRs from the concern verdict.
    """

    rule_id = "PV-04"
    rule_name = "Test Presence"
    rule_type = "deterministic"
    version = "1.1.0"

    async def evaluate(self, context: RuleContext) -> RuleResult:
        if not context or not context.pr:
            return self._missing("PRData object")

        pr = context.pr
        files = pr.files or []

        if not files:
            return self._missing("PR file list (no files returned by GitHub API)")

        # Classify files
        test_files = [f for f in files if _is_test_file(f.filename)]
        code_files = [
            f for f in files
            if not _is_test_file(f.filename) and not _is_docs_file(f.filename)
        ]
        docs_files = [f for f in files if _is_docs_file(f.filename)]

        # Track whether any patch was unknown (reduces confidence)
        has_unknown_patch = any(f.patch == "unknown" for f in files)
        confidence = 0.7 if has_unknown_patch else 1.0

        evidence: List[EvidenceItem] = []

        # --- Docs-only PR: not applicable ---
        if not code_files and not test_files and docs_files:
            evidence.append(EvidenceItem(
                source="pr_files",
                reference=f"PR #{pr.number}",
                detail=(
                    f"PR is documentation-only ({len(docs_files)} doc file(s) changed). "
                    "Test-presence rule does not apply."
                ),
                status="not_evaluated"
            ))
            return self.build_result(
                status=RuleStatus.NOT_EVALUATED,
                score=None,
                confidence=confidence,
                evidence=evidence,
                recommended_action="No action required — docs-only PR is exempt from test-coverage check."
            )

        # --- Analyse test files ---
        if test_files:
            total_additions = sum(f.additions for f in test_files)
            total_deletions = sum(f.deletions for f in test_files)
            file_list = ", ".join(f.filename for f in test_files[:8])
            if len(test_files) > 8:
                file_list += f" … (+{len(test_files) - 8} more)"

            if total_additions > total_deletions:
                # Tests grew — satisfied
                evidence.append(EvidenceItem(
                    source="pr_files",
                    reference=f"PR #{pr.number}",
                    detail=(
                        f"{len(test_files)} test file(s) added/modified with net growth "
                        f"(+{total_additions} / -{total_deletions} lines): {file_list}"
                    ),
                    status="satisfied"
                ))
                return self.build_result(
                    status=RuleStatus.SATISFIED,
                    score=100.0,
                    confidence=confidence,
                    evidence=evidence,
                    recommended_action="Test files are present and growing. Verify test quality manually."
                )
            else:
                # Test files touched but shrank or held steady
                evidence.append(EvidenceItem(
                    source="pr_files",
                    reference=f"PR #{pr.number}",
                    detail=(
                        f"{len(test_files)} test file(s) modified but net change is "
                        f"+{total_additions} / -{total_deletions} lines "
                        f"(tests did not grow): {file_list}"
                    ),
                    status="partially_satisfied"
                ))
                return self.build_result(
                    status=RuleStatus.PARTIALLY_SATISFIED,
                    score=50.0,
                    confidence=confidence,
                    evidence=evidence,
                    recommended_action=(
                        "Test files were touched but line count did not increase. "
                        "Verify that test coverage was not reduced."
                    )
                )

        # --- No test files at all ---
        code_file_list = ", ".join(f.filename for f in code_files[:8])
        if len(code_files) > 8:
            code_file_list += f" … (+{len(code_files) - 8} more)"

        evidence.append(EvidenceItem(
            source="pr_files",
            reference=f"PR #{pr.number}",
            detail=(
                f"No test files found among {len(files)} changed file(s). "
                f"Code files changed: {code_file_list}"
            ),
            status="concern"
        ))
        return self.build_result(
            status=RuleStatus.CONCERN,
            score=0.0,
            confidence=confidence,
            evidence=evidence,
            recommended_action=(
                "No test files were added or modified. Ask contributor to add or update tests "
                "covering the changed code paths."
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
            recommended_action=f"Provide {desc} to evaluate PV-04."
        )

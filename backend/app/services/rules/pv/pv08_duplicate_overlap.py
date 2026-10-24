"""
PV-08 Duplicate / Overlap Detection
-------------------------------------
Plain-logic rule (no AI). Compares changed files and added lines
across all candidate PRs to surface overlap as a signal for inspection.

Formula (documented):
  1. File overlap ratio between PR-A and PR-B:
       shared_files / union_files
     where shared_files = |files(A) ∩ files(B)|, union = |files(A) ∪ files(B)|.

  2. Line overlap ratio between PR-A and PR-B:
       shared_meaningful_lines / min(meaningful_added(A), meaningful_added(B))
     where meaningful_added = added lines that are NOT:
       - blank lines (strip == "")
       - pure opening/closing braces  ({, }, (, ), [, ])
       - import / use / require / include statements
       - lines beginning with "#", "//", "/*", "*" (comments)
     Using min() avoids penalising a large PR for sharing content with a small one.

  3. Overall similarity = max(file_overlap, line_overlap) — conservative.

Status vocabulary:
  satisfied             – no sibling PRs to compare (single-PR context)
  concern               – one or more pairs share ≥ 40 % lines/files
  not_evaluated         – fewer than 2 PRs (only current PR present)
  insufficient_evidence – patch is missing ("unknown") for this PR or all siblings

Neutral wording: "shares X% of meaningful added lines with PR #N".
Similarity is a signal for inspection, not evidence of copying.

Confidence:
  1.0 when full patches available
  0.6 when some patches are unknown (partial evidence)
  0.0 when all patches are unknown
"""

import re
from typing import List, Set, Tuple, Optional

from ..base import BaseRule
from ..contract import RuleContext, RuleResult, RuleStatus, EvidenceItem

# Lines to strip from overlap comparison (trivial)
_TRIVIAL_RE = re.compile(
    r"^\s*("                         # leading whitespace
    r"\{|\}|\(|\)|\[|\]|"            # standalone braces
    r"#.*|//.*|/\*.*|\*.*|"          # comments
    r"import\s|from\s|use\s|require\s|include\s|using\s"  # imports
    r")?\s*$"                         # trailing whitespace + blank
)

_OVERLAP_THRESHOLD = 0.40  # 40% → concern


def _extract_meaningful_added_lines(files) -> Set[str]:
    """Return set of meaningful added lines (+line) from a list of PRFile objects."""
    lines: Set[str] = set()
    for f in files:
        if not f.patch or f.patch == "unknown":
            continue
        for raw in f.patch.splitlines():
            if not raw.startswith("+") or raw.startswith("+++"):
                continue
            content = raw[1:].strip()
            if content and not _TRIVIAL_RE.match(content):
                lines.add(content)
    return lines


def _changed_filenames(files) -> Set[str]:
    return {f.filename for f in files if f.filename}


def _overlap_ratio(set_a: Set, set_b: Set) -> Optional[float]:
    """Jaccard-like for files; min-normalised for lines."""
    if not set_a or not set_b:
        return None
    union = set_a | set_b
    shared = set_a & set_b
    # Use union for file sets (Jaccard), min for line sets (conservative)
    return len(shared) / len(union)


def _line_overlap_ratio(lines_a: Set[str], lines_b: Set[str]) -> Optional[float]:
    if not lines_a or not lines_b:
        return None
    shared = lines_a & lines_b
    denom = min(len(lines_a), len(lines_b))
    return len(shared) / denom if denom else None


class DuplicateOverlapRule(BaseRule):
    """
    PV-08: Duplicate and Overlap Detection
    Compares changed files and meaningful added lines across sibling PRs.
    Reports overlap as a signal for inspection using neutral wording.
    """

    rule_id = "PV-08"
    rule_name = "Duplicate and Overlap"
    rule_type = "deterministic"
    version = "1.1.0"

    async def evaluate(self, context: RuleContext) -> RuleResult:
        if not context or not context.pr:
            return self._missing("PRData object")

        pr = context.pr
        siblings = [p for p in (context.all_prs or []) if p.number != pr.number]

        # --- Single PR context — nothing to compare ---
        if not siblings:
            return self.build_result(
                status=RuleStatus.NOT_EVALUATED,
                score=None,
                confidence=1.0,
                evidence=[EvidenceItem(
                    source="overlap_analysis",
                    reference=f"PR #{pr.number}",
                    detail="Only one candidate PR in this analysis. No overlap comparison possible.",
                    status="not_evaluated"
                )],
                recommended_action=(
                    "Submit at least 2 candidate PRs to enable overlap comparison."
                )
            )

        # --- Check if this PR's patch is entirely missing ---
        pr_files = pr.files or []
        pr_has_patches = any(f.patch and f.patch != "unknown" for f in pr_files)

        if not pr_has_patches:
            return self.build_result(
                status=RuleStatus.INSUFFICIENT_EVIDENCE,
                score=None,
                confidence=0.0,
                evidence=[EvidenceItem(
                    source="overlap_analysis",
                    reference=f"PR #{pr.number}",
                    detail=(
                        f"All {len(pr_files)} file patch(es) for PR #{pr.number} are missing or omitted by GitHub. "
                        "Cannot compute line overlap. File overlap is still reported."
                    ),
                    status="insufficient_evidence"
                )],
                recommended_action=(
                    "GitHub omitted diff patches (binary files or diff too large). "
                    "Inspect file overlap manually."
                )
            )

        pr_filenames = _changed_filenames(pr_files)
        pr_lines     = _extract_meaningful_added_lines(pr_files)

        evidence: List[EvidenceItem] = []
        max_concern = 0.0
        partial_patch = False

        for sib in siblings:
            sib_files    = sib.files or []
            sib_has_patch = any(f.patch and f.patch != "unknown" for f in sib_files)
            sib_filenames = _changed_filenames(sib_files)
            sib_lines     = _extract_meaningful_added_lines(sib_files) if sib_has_patch else set()

            # --- File overlap (always computable when filenames present) ---
            file_ratio: Optional[float] = None
            if sib_filenames and pr_filenames:
                shared_files = pr_filenames & sib_filenames
                union_files  = pr_filenames | sib_filenames
                file_ratio   = len(shared_files) / len(union_files) if union_files else None
                if file_ratio is not None:
                    evidence.append(EvidenceItem(
                        source="overlap_files",
                        reference=f"PR #{pr.number} vs PR #{sib.number}",
                        detail=(
                            f"PR #{pr.number} shares {len(shared_files)}/{len(union_files)} file(s) "
                            f"({file_ratio*100:.0f}% file overlap) with PR #{sib.number}: "
                            f"{', '.join(sorted(shared_files)[:5])}"
                            + (" …" if len(shared_files) > 5 else "")
                        ),
                        status="concern" if file_ratio >= _OVERLAP_THRESHOLD else "satisfied"
                    ))

            # --- Line overlap ---
            if not sib_has_patch:
                partial_patch = True
                evidence.append(EvidenceItem(
                    source="overlap_lines",
                    reference=f"PR #{pr.number} vs PR #{sib.number}",
                    detail=(
                        f"Line-level overlap with PR #{sib.number} cannot be computed: "
                        "patch data is missing for that PR."
                    ),
                    status="insufficient_evidence"
                ))
                line_ratio = None
            else:
                line_ratio = _line_overlap_ratio(pr_lines, sib_lines)
                if line_ratio is not None:
                    evidence.append(EvidenceItem(
                        source="overlap_lines",
                        reference=f"PR #{pr.number} vs PR #{sib.number}",
                        detail=(
                            f"PR #{pr.number} shares {line_ratio*100:.0f}% of meaningful added lines "
                            f"with PR #{sib.number} "
                            f"({len(pr_lines & sib_lines)} shared / "
                            f"min({len(pr_lines)}, {len(sib_lines)}) = {min(len(pr_lines), len(sib_lines))} lines). "
                            "Similarity is a signal for inspection, not evidence of copying."
                        ),
                        status="concern" if line_ratio >= _OVERLAP_THRESHOLD else "satisfied"
                    ))

            ratios = [r for r in [file_ratio, line_ratio] if r is not None]
            if ratios:
                max_concern = max(max_concern, max(ratios))

        confidence = 0.6 if partial_patch else 1.0

        # Determine overall status
        if max_concern >= _OVERLAP_THRESHOLD:
            return self.build_result(
                status=RuleStatus.CONCERN,
                score=round((1.0 - max_concern) * 100, 1),
                confidence=confidence,
                evidence=evidence,
                recommended_action=(
                    f"High overlap detected (up to {max_concern*100:.0f}%). "
                    "Inspect both PRs for duplicated work. This is a signal, not a verdict."
                )
            )

        if partial_patch and max_concern == 0.0:
            return self.build_result(
                status=RuleStatus.INSUFFICIENT_EVIDENCE,
                score=None,
                confidence=confidence,
                evidence=evidence,
                recommended_action=(
                    "Some patch data was missing. File overlap was computed where possible. "
                    "Inspect manually."
                )
            )

        return self.build_result(
            status=RuleStatus.SATISFIED,
            score=round((1.0 - max_concern) * 100, 1),
            confidence=confidence,
            evidence=evidence,
            recommended_action=(
                f"No significant overlap detected (max {max_concern*100:.0f}% across all comparisons)."
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
            recommended_action=f"Provide {desc} to evaluate PV-08."
        )

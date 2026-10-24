"""
PV Scope Pass
-------------
Plain-logic rule (no AI). Two distinct checks:

1. NOISY FILES: Changed files that are build artifacts, generated output, or
   dependency lock files. These don't reflect the author's implementation
   intent and can obscure review scope.
   Label: "noisy" — not "unrelated".

   Noisy patterns (path heuristics):
     - package-lock.json, yarn.lock, poetry.lock, Pipfile.lock, Gemfile.lock,
       composer.lock, cargo.lock, etc.
     - dist/, build/, __pycache__/, *.min.js, *.min.css, *.bundle.js
     - *.pyc, *.egg-info/, .DS_Store, Thumbs.db, *.log
     - node_modules/ (should never appear in a PR but guard anyway)

2. SCOPE CHECK: Checks whether the changed non-noisy files and their
   identifiers (function/class names extracted from filenames) appear in
   the issue title or body. Files with NO connection to issue text are
   flagged for inspection — they may be unrelated changes included
   inadvertently.
   Label: "possibly unrelated to issue" — not "unrelated".

Status vocabulary:
  satisfied             – all code files appear scope-connected; no/few noisy files
  partially_satisfied   – some scope-unconnected files; minor noisy files present
  concern               – many scope-unconnected files or significant noisy files
  not_evaluated         – no file data or issue text unavailable
  insufficient_evidence – patch data missing across the board

Confidence:
  1.0 full file data and issue text available
  0.7 issue body missing (title only)
  0.5 partial file data
"""

import re
from typing import List, Set, Tuple

from ..base import BaseRule
from ..contract import RuleContext, RuleResult, RuleStatus, EvidenceItem

# --- Noisy file patterns ---
_NOISY_FILENAME_RE = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|poetry\.lock|Pipfile\.lock|"
    r"Gemfile\.lock|composer\.lock|Cargo\.lock|shrinkwrap\.json|"
    r".*\.min\.(js|css)|.*\.bundle\.(js|css)|.*\.pyc|.*\.egg-info|"
    r"\.DS_Store|Thumbs\.db|.*\.log)"
    r"$",
    re.IGNORECASE,
)
_NOISY_DIR_RE = re.compile(
    r"^(dist|build|__pycache__|node_modules|\.eggs|\.mypy_cache|\.pytest_cache|"
    r"\.tox|\.venv|venv|env|coverage|htmlcov)/",
    re.IGNORECASE,
)

# Threshold: if ≥ this fraction of code files look unrelated → concern
_SCOPE_CONCERN_THRESHOLD = 0.50
_NOISY_CONCERN_COUNT = 3  # flag if more than this many noisy files


def _is_noisy(filename: str) -> bool:
    return bool(_NOISY_FILENAME_RE.search(filename) or _NOISY_DIR_RE.match(filename))


def _stem_tokens(filename: str) -> Set[str]:
    """
    Extract lowercase tokens from a filename/path for scope matching.
    e.g. "backend/app/services/cache_service.py" →
         {"backend", "app", "services", "cache", "service", "py"}
    """
    base = filename.split("/")[-1]
    stem = re.sub(r"\.[^.]+$", "", base)        # remove extension
    parts = re.split(r"[_\-\. ]+", stem.lower()) # split by separators
    # also add path components
    path_parts = [p.lower() for p in filename.replace("\\", "/").split("/")]
    return set(parts) | set(path_parts) - {"", "py", "js", "ts", "go", "rb", "java", "cs", "cpp"}


def _issue_tokens(issue) -> Set[str]:
    """Lowercase word tokens from issue title + body."""
    text = (issue.title or "")
    if issue.body:
        text += " " + issue.body
    return set(re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()))


class ScopePassRule(BaseRule):
    """
    PV Scope Pass
    Flags noisy files (lockfiles, build output) and files that appear
    scope-disconnected from the issue text. Uses path heuristics only; no AI.
    """

    rule_id = "PV-SCOPE"
    rule_name = "Scope Pass"
    rule_type = "deterministic"
    version = "1.1.0"

    async def evaluate(self, context: RuleContext) -> RuleResult:
        if not context or not context.pr:
            return self._missing("PRData object")

        pr = context.pr
        files = pr.files or []

        if not files:
            return self.build_result(
                status=RuleStatus.NOT_EVALUATED,
                score=None,
                confidence=0.0,
                evidence=[EvidenceItem(
                    source="scope_analysis",
                    reference=f"PR #{pr.number}",
                    detail="No file data available — cannot assess scope.",
                    status="not_evaluated"
                )],
                recommended_action="Provide PR file list to evaluate scope."
            )

        issue = context.issue
        issue_tok = _issue_tokens(issue) if issue else set()
        has_issue_text = bool(issue and (issue.title or issue.body))
        confidence = 1.0 if has_issue_text else 0.7
        if has_issue_text and not (issue.body or "").strip():
            confidence = 0.7  # title-only

        noisy_files  = []
        code_files   = []
        unrelated_files = []
        evidence: List[EvidenceItem] = []
        has_unknown_patches = sum(1 for f in files if f.patch == "unknown")
        if has_unknown_patches:
            confidence = min(confidence, 0.5)

        for f in files:
            fname = f.filename

            if _is_noisy(fname):
                noisy_files.append(fname)
                evidence.append(EvidenceItem(
                    source="scope_noisy",
                    reference=f"{fname}",
                    detail=(
                        f"'{fname}' is a noisy file (lockfile, build artifact, or generated output). "
                        "These are common but inflate PR diff size. Consider separating them."
                    ),
                    status="concern"
                ))
                continue

            code_files.append(fname)

            # Scope check: do file path tokens appear in issue text?
            if issue_tok:
                file_tok = _stem_tokens(fname)
                if not (file_tok & issue_tok):
                    unrelated_files.append(fname)
                    evidence.append(EvidenceItem(
                        source="scope_check",
                        reference=f"{fname}",
                        detail=(
                            f"'{fname}' — no tokens from its path appear in the issue text. "
                            "It may be an unrelated change; inspect to confirm."
                        ),
                        status="concern"
                    ))
                else:
                    evidence.append(EvidenceItem(
                        source="scope_check",
                        reference=f"{fname}",
                        detail=f"'{fname}' — path tokens match issue text (scope-connected).",
                        status="satisfied"
                    ))

        # Compute summary
        total_code = len(code_files)
        n_noisy    = len(noisy_files)
        n_unrelated = len(unrelated_files)

        # Prepend summary line
        evidence.insert(0, EvidenceItem(
            source="scope_summary",
            reference=f"PR #{pr.number}",
            detail=(
                f"PR #{pr.number}: {len(files)} file(s) total — "
                f"{total_code} code file(s), {n_noisy} noisy file(s), "
                f"{n_unrelated} scope-disconnected code file(s). "
                + ("Issue text available for scope matching." if has_issue_text else "No issue text; scope matching skipped.")
            ),
            status="satisfied" if n_noisy == 0 and n_unrelated == 0 else "concern"
        ))

        is_noisy_concern   = n_noisy > _NOISY_CONCERN_COUNT
        scope_ratio        = n_unrelated / total_code if total_code else 0.0
        is_scope_concern   = scope_ratio >= _SCOPE_CONCERN_THRESHOLD and has_issue_text

        if is_noisy_concern or is_scope_concern:
            return self.build_result(
                status=RuleStatus.CONCERN,
                score=round((1.0 - max(scope_ratio, min(n_noisy / 10.0, 1.0))) * 100, 1),
                confidence=confidence,
                evidence=evidence,
                recommended_action=(
                    (f"{n_noisy} noisy file(s) detected. " if n_noisy else "")
                    + (f"{n_unrelated}/{total_code} code file(s) appear scope-disconnected from the issue. " if is_scope_concern else "")
                    + "Review carefully before merging."
                )
            )

        if n_noisy > 0 or n_unrelated > 0:
            return self.build_result(
                status=RuleStatus.PARTIALLY_SATISFIED,
                score=round((1.0 - max(scope_ratio, n_noisy / 10.0)) * 100, 1),
                confidence=confidence,
                evidence=evidence,
                recommended_action=(
                    (f"{n_noisy} noisy file(s) present (minor). " if n_noisy else "")
                    + (f"{n_unrelated} code file(s) may be unrelated — verify. " if n_unrelated else "")
                )
            )

        return self.build_result(
            status=RuleStatus.SATISFIED,
            score=100.0,
            confidence=confidence,
            evidence=evidence,
            recommended_action="All changed files appear to be within scope. No noisy files detected."
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
            recommended_action=f"Provide {desc} to evaluate PV-SCOPE."
        )

"""
tests/test_pv_rules.py
-----------------------
Tests for Sub-step A plain-logic PV rules.

Coverage:
  PV-04 Test Presence:
    - tests added (satisfied)
    - tests shrunk (partially_satisfied)
    - no tests (concern)
    - docs-only PR (not_evaluated)
    - missing file data (insufficient_evidence)

  PV-05 CI Status:
    - all checks pass (satisfied)
    - one check fails (critical_flag)
    - checks pending (concern)
    - no CI configured (not_evaluated)
    - missing CI data (insufficient_evidence)

  PV-08 Duplicate Overlap:
    - single PR, no siblings (not_evaluated)
    - two near-identical PRs (concern)
    - two distinct PRs (satisfied)
    - missing patch on this PR (insufficient_evidence)
    - sibling has missing patch (partial evidence, uses file overlap)

  PV-SCOPE Scope Pass:
    - all files scope-connected (satisfied)
    - lockfile present (noisy → partially_satisfied)
    - many lockfiles (noisy → concern)
    - many unrelated files (concern)
    - no issue text (not_evaluated path — confidence drops to 0.7)
    - very large PR (still evaluates, high file count)
    - no file data (not_evaluated)
"""

import pytest
from backend.app.services.rules.contract import RuleContext, RuleStatus
from backend.app.services.rules.pv.pv04_test_presence import TestPresenceRule
from backend.app.services.rules.pv.pv05_ci_status import CIStatusRule
from backend.app.services.rules.pv.pv08_duplicate_overlap import DuplicateOverlapRule
from backend.app.services.rules.pv.pv_scope_pass import ScopePassRule
from backend.app.models import (
    IssueData,
    PRData,
    PRFile,
    CIStatus,
    CheckRunItem,
    MaintainerFetchResponse,
)

# ─────────────────────────── helpers ─────────────────────────────

def make_issue(title="Fix cache invalidation bug", body="The cache does not invalidate on update in the cache_service module.") -> IssueData:
    return IssueData(
        number=42,
        title=title,
        body=body,
        state="open",
        labels=["bug"],
        assignees=[],
        author="maintainer",
        url="https://github.com/org/repo/issues/42"
    )


def make_file(filename, additions=10, deletions=2, patch="+new line\n+another line") -> PRFile:
    return PRFile(filename=filename, status="modified", additions=additions, deletions=deletions, patch=patch)


def make_ci(*checks) -> CIStatus:
    """checks: list of (name, status, conclusion) tuples"""
    runs = [CheckRunItem(name=n, status=s, conclusion=c) for n, s, c in checks]
    return CIStatus(total_checks=len(runs), state="unknown", check_runs=runs)


def make_pr(number=1, files=None, ci=None, url=None) -> PRData:
    return PRData(
        number=number,
        url=url or f"https://github.com/org/repo/pull/{number}",
        title=f"Fix: cache invalidation PR {number}",
        body="Fixes #42",
        state="open",
        author="contributor",
        additions=sum(f.additions for f in (files or [])),
        deletions=sum(f.deletions for f in (files or [])),
        changed_files_count=len(files or []),
        files=files or [],
        ci_status=ci or CIStatus()
    )


def ctx(pr, issue=None, siblings=None) -> RuleContext:
    return RuleContext(
        issue=issue or make_issue(),
        pr=pr,
        all_prs=[pr] + (siblings or [])
    )


# ═══════════════════════════════════════════════════════════════════
#  PV-04 TEST PRESENCE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pv04_tests_added():
    """Tests added with net growth → satisfied."""
    files = [
        make_file("src/cache_service.py", additions=15, deletions=3),
        make_file("tests/test_cache_service.py", additions=20, deletions=0),
    ]
    r = await TestPresenceRule().evaluate(ctx(make_pr(files=files)))
    assert r.rule_id == "PV-04"
    assert r.status == RuleStatus.SATISFIED
    assert r.confidence == 1.0
    assert any("20" in e.detail for e in r.evidence)


@pytest.mark.asyncio
async def test_pv04_tests_shrunk():
    """Test file touched but deletions > additions → partially_satisfied."""
    files = [
        make_file("src/cache.py", additions=10, deletions=0),
        make_file("tests/test_cache.py", additions=2, deletions=15),
    ]
    r = await TestPresenceRule().evaluate(ctx(make_pr(files=files)))
    assert r.status == RuleStatus.PARTIALLY_SATISFIED
    assert r.score == 50.0


@pytest.mark.asyncio
async def test_pv04_no_tests():
    """No test files → concern."""
    files = [make_file("src/utils.py"), make_file("src/helpers.py")]
    r = await TestPresenceRule().evaluate(ctx(make_pr(files=files)))
    assert r.status == RuleStatus.CONCERN
    assert r.score == 0.0


@pytest.mark.asyncio
async def test_pv04_docs_only():
    """Docs-only PR is not penalised → not_evaluated."""
    files = [
        make_file("README.md", patch="+ added doc line"),
        make_file("docs/setup.md", patch="+ setup info"),
    ]
    r = await TestPresenceRule().evaluate(ctx(make_pr(files=files)))
    assert r.status == RuleStatus.NOT_EVALUATED


@pytest.mark.asyncio
async def test_pv04_missing_files():
    """No file list → insufficient_evidence."""
    pr = make_pr(files=[])
    r = await TestPresenceRule().evaluate(ctx(pr))
    assert r.status == RuleStatus.INSUFFICIENT_EVIDENCE
    assert r.confidence == 0.0


@pytest.mark.asyncio
async def test_pv04_missing_patch_reduces_confidence():
    """Unknown patches reduce confidence but rule still evaluates on filenames."""
    files = [
        make_file("src/main.py", patch="unknown"),
        make_file("tests/test_main.py", additions=10, deletions=0, patch="unknown"),
    ]
    r = await TestPresenceRule().evaluate(ctx(make_pr(files=files)))
    # Test file present, so satisfies or partially satisfies; confidence reduced
    assert r.confidence == 0.7
    assert r.status in (RuleStatus.SATISFIED, RuleStatus.PARTIALLY_SATISFIED)


# ═══════════════════════════════════════════════════════════════════
#  PV-05 CI STATUS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pv05_all_pass():
    """All checks pass → satisfied."""
    ci = make_ci(
        ("lint", "completed", "success"),
        ("tests", "completed", "success"),
    )
    r = await CIStatusRule().evaluate(ctx(make_pr(ci=ci)))
    assert r.status == RuleStatus.SATISFIED
    assert r.score == 100.0


@pytest.mark.asyncio
async def test_pv05_failing_ci():
    """Failing CI → critical_flag (not auto-rejected)."""
    ci = make_ci(
        ("lint", "completed", "success"),
        ("tests", "completed", "failure"),
    )
    r = await CIStatusRule().evaluate(ctx(make_pr(ci=ci)))
    assert r.status == RuleStatus.CRITICAL_FLAG
    assert r.score == 0.0
    # Evidence should call it a critical flag, not a blocker/rejection
    assert any("CRITICAL FLAG" in e.detail for e in r.evidence)
    assert not any("reject" in e.detail.lower() for e in r.evidence)


@pytest.mark.asyncio
async def test_pv05_pending_ci():
    """Pending checks → concern."""
    ci = make_ci(
        ("tests", "in_progress", ""),
        ("lint", "queued", ""),
    )
    r = await CIStatusRule().evaluate(ctx(make_pr(ci=ci)))
    assert r.status == RuleStatus.CONCERN
    assert r.confidence == 0.7


@pytest.mark.asyncio
async def test_pv05_no_ci():
    """No CI configured → not_evaluated."""
    r = await CIStatusRule().evaluate(ctx(make_pr(ci=CIStatus(total_checks=0))))
    assert r.status == RuleStatus.NOT_EVALUATED


@pytest.mark.asyncio
async def test_pv05_missing_pr():
    """Missing PRData → insufficient_evidence."""
    r = await CIStatusRule().evaluate(RuleContext(issue=make_issue(), pr=None))
    assert r.status == RuleStatus.INSUFFICIENT_EVIDENCE
    assert r.confidence == 0.0


# ═══════════════════════════════════════════════════════════════════
#  PV-08 DUPLICATE OVERLAP
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pv08_single_pr():
    """No siblings → not_evaluated."""
    files = [make_file("src/cache.py", patch="+meaningful fix line")]
    pr = make_pr(files=files)
    r = await DuplicateOverlapRule().evaluate(RuleContext(issue=make_issue(), pr=pr, all_prs=[pr]))
    assert r.status == RuleStatus.NOT_EVALUATED


@pytest.mark.asyncio
async def test_pv08_near_identical_prs():
    """Two PRs with heavily overlapping added lines → concern."""
    shared_patch = "\n".join(f"+meaningful implementation line {i}" for i in range(20))
    files_a = [make_file("src/cache.py", additions=20, patch=shared_patch)]
    files_b = [make_file("src/cache.py", additions=20, patch=shared_patch)]
    pr_a = make_pr(1, files=files_a)
    pr_b = make_pr(2, files=files_b)
    r = await DuplicateOverlapRule().evaluate(RuleContext(issue=make_issue(), pr=pr_a, all_prs=[pr_a, pr_b]))
    assert r.status == RuleStatus.CONCERN
    # Check neutral wording — no "copied"
    for e in r.evidence:
        assert "copied" not in e.detail.lower()
    assert any("shares" in e.detail for e in r.evidence)


@pytest.mark.asyncio
async def test_pv08_distinct_prs():
    """Two PRs touching different files → satisfied."""
    files_a = [make_file("src/auth.py", patch="+auth specific logic line one\n+auth specific logic line two")]
    files_b = [make_file("src/cache.py", patch="+cache specific logic alpha\n+cache specific logic beta")]
    pr_a = make_pr(1, files=files_a)
    pr_b = make_pr(2, files=files_b)
    r = await DuplicateOverlapRule().evaluate(RuleContext(issue=make_issue(), pr=pr_a, all_prs=[pr_a, pr_b]))
    assert r.status == RuleStatus.SATISFIED


@pytest.mark.asyncio
async def test_pv08_missing_patch_this_pr():
    """This PR has all patches missing → insufficient_evidence (never 0%)."""
    files = [make_file("src/cache.py", patch="unknown")]
    pr = make_pr(files=files)
    sibling = make_pr(2, files=[make_file("src/cache.py", patch="+sibling line one")])
    r = await DuplicateOverlapRule().evaluate(RuleContext(issue=make_issue(), pr=pr, all_prs=[pr, sibling]))
    assert r.status == RuleStatus.INSUFFICIENT_EVIDENCE
    # Score must not be 0.0 (which would imply 100% overlap)
    assert r.score is None


@pytest.mark.asyncio
async def test_pv08_sibling_missing_patch():
    """Sibling has missing patch → partial evidence reported, not 0% overlap."""
    files = [make_file("src/cache.py", patch="+this pr adds meaningful line one")]
    pr = make_pr(files=files)
    sibling = make_pr(2, files=[make_file("src/cache.py", patch="unknown")])
    r = await DuplicateOverlapRule().evaluate(RuleContext(issue=make_issue(), pr=pr, all_prs=[pr, sibling]))
    # Should have file overlap evidence but insufficient_evidence for line overlap
    assert any("insufficient_evidence" in (e.status or "") for e in r.evidence)
    # Status should not be satisfied if file overlap exists
    assert r.status != RuleStatus.SATISFIED or r.confidence < 1.0


# ═══════════════════════════════════════════════════════════════════
#  PV-SCOPE PASS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scope_all_connected():
    """All files relate to issue text → satisfied."""
    issue = make_issue(title="Fix cache invalidation bug", body="cache_service module needs update")
    files = [
        make_file("backend/app/services/cache_service.py"),
        make_file("tests/test_cache_service.py"),
    ]
    r = await ScopePassRule().evaluate(ctx(make_pr(files=files), issue=issue))
    assert r.status == RuleStatus.SATISFIED


@pytest.mark.asyncio
async def test_scope_lockfile_noisy():
    """Lockfile present → labelled noisy, not 'unrelated'."""
    issue = make_issue()
    files = [
        make_file("src/cache.py"),
        make_file("package-lock.json"),
    ]
    r = await ScopePassRule().evaluate(ctx(make_pr(files=files), issue=issue))
    assert r.status in (RuleStatus.PARTIALLY_SATISFIED, RuleStatus.CONCERN)
    noisy_evidence = [e for e in r.evidence if "noisy" in e.detail.lower()]
    assert noisy_evidence, "Expected 'noisy' label in evidence"
    # Should never say "unrelated"
    for e in r.evidence:
        assert "unrelated" not in e.detail.lower()


@pytest.mark.asyncio
async def test_scope_many_lockfiles():
    """Many noisy files → concern."""
    files = [make_file(f"lock{i}.lock") for i in range(5)]
    r = await ScopePassRule().evaluate(ctx(make_pr(files=files)))
    assert r.status == RuleStatus.CONCERN


@pytest.mark.asyncio
async def test_scope_no_file_data():
    """No files → not_evaluated."""
    r = await ScopePassRule().evaluate(ctx(make_pr(files=[])))
    assert r.status == RuleStatus.NOT_EVALUATED


@pytest.mark.asyncio
async def test_scope_no_issue_text():
    """No issue body/title — scope matching skipped, confidence reduced."""
    issue = IssueData(number=1, title="", body=None, state="open", labels=[], assignees=[], author="x", url="https://github.com/org/repo/issues/1")
    files = [make_file("src/random_module.py")]
    r = await ScopePassRule().evaluate(ctx(make_pr(files=files), issue=issue))
    assert r.confidence <= 0.7
    # Should not show "unrelated" findings since matching was skipped
    scope_concerns = [e for e in r.evidence if e.source == "scope_check" and "concern" in (e.status or "")]
    assert not scope_concerns


@pytest.mark.asyncio
async def test_scope_very_large_pr():
    """Very large PR (100+ files) still evaluates without error."""
    issue = make_issue(title="Refactor cache module", body="cache module refactor needed")
    files = [make_file(f"src/module_{i}.py", additions=5, deletions=0) for i in range(120)]
    files.append(make_file("yarn.lock"))  # one noisy file
    r = await ScopePassRule().evaluate(ctx(make_pr(files=files), issue=issue))
    # Rule should complete without exception
    assert r.status is not None
    assert r.rule_id == "PV-SCOPE"


# ═══════════════════════════════════════════════════════════════════
#  PV ENGINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pv_engine_full_run():
    """Integration: engine runs all 4 rules, returns one report per PR, correctly labelled."""
    from backend.app.services.pv_engine import run_plain_logic_analysis
    from backend.app.models import MaintainerFetchResponse

    issue = make_issue()
    pr1_files = [
        make_file("src/cache.py"),
        make_file("tests/test_cache.py", additions=10, deletions=0),
    ]
    pr2_files = [
        make_file("src/cache.py"),  # overlaps with pr1
        make_file("package-lock.json"),  # noisy
    ]
    ci_pass = make_ci(("tests", "completed", "success"))
    ci_fail = make_ci(("tests", "completed", "failure"))

    pr1 = make_pr(1, files=pr1_files, ci=ci_pass)
    pr2 = make_pr(2, files=pr2_files, ci=ci_fail)

    fetch_response = MaintainerFetchResponse(
        cached=False,
        fetched_at="2026-01-01T00:00:00Z",
        issue=issue,
        pull_requests=[pr1, pr2],
        warnings=[]
    )

    report = await run_plain_logic_analysis(fetch_response)

    assert report.analysis_type == "sub_step_a_plain_logic"
    assert len(report.pr_reports) == 2

    # Each report has all 4 rules
    for pr_report in report.pr_reports:
        rule_ids = {r.rule_id for r in pr_report.rule_results}
        assert rule_ids == {"PV-04", "PV-05", "PV-08", "PV-SCOPE"}

    # PR2 should have critical_flag for CI
    pr2_report = next(r for r in report.pr_reports if r.pr_number == 2)
    ci_result = next(r for r in pr2_report.rule_results if r.rule_id == "PV-05")
    assert ci_result.status == RuleStatus.CRITICAL_FLAG

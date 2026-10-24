import pytest
from backend.app.models import IssueData
from backend.app.services.rules import (
    RuleRunner,
    RuleContext,
    RuleStatus,
    DummyCheckRule,
    BaseRule
)

@pytest.mark.asyncio
async def test_dm01_dummy_rule_normal():
    """Normal test: complete valid issue with descriptive title."""
    runner = RuleRunner()
    runner.register(DummyCheckRule())

    valid_issue = IssueData(
        number=42,
        title="Fix connection timeout in retry loop",
        url="https://github.com/example/repo/issues/42",
        state="open"
    )
    context = RuleContext(issue=valid_issue)

    result = await runner.run_rule("DM-01", context)

    assert result.rule_id == "DM-01"
    assert result.status == RuleStatus.PASS
    assert result.score == 1.0
    assert result.confidence == 1.0
    assert len(result.evidence) == 1
    assert result.evidence[0].source == "issue_title"
    assert result.evidence[0].reference == "issue:42"
    assert "satisfies basic descriptive" in result.recommended_action
    assert result.metadata.execution_type == "deterministic"
    assert result.metadata.rule_version == "1.0.0"

@pytest.mark.asyncio
async def test_dm01_dummy_rule_edge_case_missing_data():
    """Edge-case test: missing issue and empty title handled safely per SH-03."""
    runner = RuleRunner()
    runner.register(DummyCheckRule())

    # Case A: empty context (missing issue)
    context_empty = RuleContext(issue=None)
    result_empty = await runner.run_rule("DM-01", context_empty)

    assert result_empty.rule_id == "DM-01"
    assert result_empty.status == RuleStatus.UNKNOWN
    assert result_empty.confidence == 0.0
    assert result_empty.score is None
    assert len(result_empty.evidence) == 1
    assert "Missing or insufficient data" in result_empty.evidence[0].detail

    # Case B: issue with empty title
    issue_blank = IssueData(
        number=99,
        title="   ",
        url="https://github.com/example/repo/issues/99",
        state="open"
    )
    result_blank = await runner.run_rule("DM-01", RuleContext(issue=issue_blank))
    assert result_blank.status == RuleStatus.UNKNOWN
    assert result_blank.confidence == 0.0

@pytest.mark.asyncio
async def test_rule_runner_defensive_boundary():
    """Verifies that an unhandled exception in a rule is caught safely and fails closed."""
    class FaultyRule(BaseRule):
        rule_id = "FAULTY-01"
        async def evaluate(self, context: RuleContext):
            raise RuntimeError("Unexpected external connection error")

    runner = RuleRunner()
    runner.register(FaultyRule())

    result = await runner.run_rule("FAULTY-01", RuleContext())
    assert result.rule_id == "FAULTY-01"
    assert result.status == RuleStatus.UNKNOWN
    assert result.confidence == 0.0
    assert any("runner_exception" in ev.source for ev in result.evidence)

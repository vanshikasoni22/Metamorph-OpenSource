"""
tests/test_beginner_plan.py
---------------------------
Tests for Phase 4 Sub-step A: Beginner Plan Generation (CG-01, CG-02, CG-03).

Covers all 5 rules specified in the plan approval:
  1. No hardcoded fallback when Qwen fails -> clear "plan unavailable" error.
  2. HTTP 402 handling -> clear message about provider billing/credit limit.
  3. Reject tasks with requirement_id not in real list; task IDs generated in code.
  4. relevant_files kept only if they exist in repo evidence, otherwise 'unknown'.
  5. Injects missing set_up, test, submit template tasks.
  + Rule 6: Estimated times are ranges labelled as estimates.
  + CG-02 fixed category ordering.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from backend.app.main import app
from backend.app.models import (
    PlanRequest,
    BeginnerPlan,
    QwenPlanOutput,
    BeginnerProfileInput,
)
from backend.app.services.plan_service import (
    generate_beginner_plan,
    _validate_requirement_ids,
    _validate_relevant_files,
    _ensure_time_range,
    _inject_missing_templates,
    _sort_by_category,
    _assign_task_ids,
    CATEGORY_ORDER,
)
from backend.app.services.llm_client import (
    LLMError,
    LLMPaymentRequiredError,
    LLMValidationError,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_plan.db")
    monkeypatch.setattr("backend.app.config.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.database.DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.config.DATABASE_URL", f"sqlite:///{test_db}")
    monkeypatch.setattr("backend.app.database.DATABASE_URL", f"sqlite:///{test_db}")
    from backend.app.database import init_db
    init_db()


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1: No hardcoded fallback on Qwen failure -> clear error
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rule1_no_hardcoded_fallback_on_qwen_failure():
    """
    Rule 1: When Qwen fails, do NOT fall back to generic hardcoded steps.
    Raise an LLMError with a clear 'plan unavailable, please try again' message.
    """
    mock_client = MagicMock()
    mock_client.complete_structured = AsyncMock(
        side_effect=LLMError("Connection refused by upstream provider")
    )

    req = PlanRequest(
        username="alice",
        issue_url="https://github.com/fastapi/fastapi/issues/100",
        requirement_list=[{"id": "R1", "description": "Fix bug in routing"}],
    )

    with pytest.raises(LLMError) as exc_info:
        await generate_beginner_plan(req, qwen_client=mock_client)

    msg = str(exc_info.value).lower()
    assert "plan generation unavailable" in msg or "plan unavailable" in msg
    assert "try again" in msg


@pytest.mark.asyncio
async def test_rule1_endpoint_returns_503_on_qwen_failure():
    """
    Rule 1 (Endpoint): POST /beginner/plan returns 503 when plan is unavailable.
    """
    mock_client = MagicMock()
    mock_client.complete_structured = AsyncMock(
        side_effect=LLMError("Model rate limit")
    )

    payload = {
        "username": "alice",
        "issue_url": "https://github.com/fastapi/fastapi/issues/100",
        "requirement_list": [{"id": "R1", "description": "Fix routing bug"}],
    }

    from backend.app.services import plan_service
    orig_get_client = plan_service.get_qwen_client
    plan_service.get_qwen_client = lambda: mock_client

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/beginner/plan", json=payload)
            assert resp.status_code == 503
            data = resp.json()
            assert "plan unavailable" in data["detail"].lower()
    finally:
        plan_service.get_qwen_client = orig_get_client


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2: Handle HTTP 402 with clear provider billing/credit limit message
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rule2_handle_http_402_billing_limit():
    """
    Rule 2: HTTP 402 from provider raises LLMPaymentRequiredError and
    endpoint returns 402 with clear billing/credit limit message.
    """
    mock_client = MagicMock()
    mock_client.complete_structured = AsyncMock(
        side_effect=LLMPaymentRequiredError(
            "OpenRouter payment required: Credit balance is too low."
        )
    )

    req = PlanRequest(
        username="bob",
        issue_url="https://github.com/psf/requests/issues/200",
        requirement_list=[{"id": "R1", "description": "Improve timeout docs"}],
    )

    # Service layer re-raises LLMPaymentRequiredError
    with pytest.raises(LLMPaymentRequiredError):
        await generate_beginner_plan(req, qwen_client=mock_client)

    # Endpoint layer returns 402
    from backend.app.services import plan_service
    orig_get_client = plan_service.get_qwen_client
    plan_service.get_qwen_client = lambda: mock_client

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/beginner/plan",
                json={
                    "username": "bob",
                    "issue_url": "https://github.com/psf/requests/issues/200",
                    "requirement_list": [{"id": "R1", "description": "Improve timeout docs"}],
                },
            )
            assert resp.status_code == 402
            data = resp.json()
            assert "billing" in data["detail"].lower() or "credit" in data["detail"].lower()
    finally:
        plan_service.get_qwen_client = orig_get_client


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3: Reject tasks with invalid requirement_id; generate task IDs in code
# ─────────────────────────────────────────────────────────────────────────────

def test_rule3_reject_invalid_requirement_ids():
    """
    Rule 3: Any task whose requirement_id is not in the real requirement list is rejected.
    """
    valid_req_ids = {"R1", "R2"}
    tasks = [
        {"title": "Valid task 1", "requirement_id": "R1"},
        {"title": "Invented task", "requirement_id": "R99"},  # not in list
        {"title": "Empty req task", "requirement_id": ""},     # empty
        {"title": "None req task", "requirement_id": None},    # None
        {"title": "Valid task 2", "requirement_id": "R2"},
    ]

    filtered = _validate_requirement_ids(tasks, valid_req_ids)
    assert len(filtered) == 2
    assert [t["requirement_id"] for t in filtered] == ["R1", "R2"]


def test_rule3_generate_task_ids_in_code():
    """
    Rule 3: Task IDs are generated in code (T-01, T-02, ...), overriding any Qwen IDs.
    """
    tasks = [
        {"task_id": "QWEN_INVENTED_1", "title": "First"},
        {"task_id": "CUSTOM_ID_XYZ", "title": "Second"},
        {"title": "Third without id"},
    ]
    assigned = _assign_task_ids(tasks)
    assert assigned[0]["task_id"] == "T-01"
    assert assigned[1]["task_id"] == "T-02"
    assert assigned[2]["task_id"] == "T-03"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4: Keep relevant_files only if in repo evidence, otherwise 'unknown'
# ─────────────────────────────────────────────────────────────────────────────

def test_rule4_validate_relevant_files_against_evidence():
    """
    Rule 4: Keep relevant_files only if they exist in fetched repository evidence,
    otherwise replace with 'unknown'.
    """
    repo_evidence = {"src/app.py", "README.md", "tests/test_app.py"}

    tasks = [
        {
            "title": "Task 1",
            "relevant_files": ["src/app.py", "imaginary/file.py", "secret.env"],
        },
        {
            "title": "Task 2",
            "relevant_files": ["README.md"],
        },
        {
            "title": "Task 3 (all fake)",
            "relevant_files": ["fake1.js", "fake2.css"],
        },
        {
            "title": "Task 4 (already unknown)",
            "relevant_files": ["unknown"],
        },
    ]

    validated = _validate_relevant_files(tasks, repo_evidence)

    # Task 1: kept real file, replaced fakes with single deduplicated 'unknown'
    assert validated[0]["relevant_files"] == ["src/app.py", "unknown"]
    # Task 2: valid file kept
    assert validated[1]["relevant_files"] == ["README.md"]
    # Task 3: all fakes became deduplicated 'unknown'
    assert validated[2]["relevant_files"] == ["unknown"]
    # Task 4: stays 'unknown'
    assert validated[3]["relevant_files"] == ["unknown"]


def test_rule4_empty_evidence_makes_all_unknown():
    """
    Rule 4: When repo evidence is empty or None, all file paths become 'unknown'.
    """
    tasks = [
        {"title": "Task", "relevant_files": ["src/main.py", "config.json"]}
    ]
    validated = _validate_relevant_files(tasks, set())
    assert validated[0]["relevant_files"] == ["unknown"]


# ─────────────────────────────────────────────────────────────────────────────
# Rule 5: Inject missing set_up, test, submit template tasks
# ─────────────────────────────────────────────────────────────────────────────

def test_rule5_inject_missing_templates():
    """
    Rule 5: If Qwen omits set up, test, or submit tasks, inject them from
    a fixed template with is_template=True.
    """
    # Qwen only provided 'investigate' and 'implement'
    qwen_tasks = [
        {"category": "investigate", "title": "Check logs"},
        {"category": "implement", "title": "Add retry loop"},
    ]

    injected = _inject_missing_templates(
        qwen_tasks,
        repo_name="org/myrepo",
        contributing_hint="See CONTRIBUTING.md for details.",
    )

    categories = [t["category"] for t in injected]
    assert "set_up" in categories
    assert "test" in categories
    assert "submit" in categories

    # Check template flags
    template_tasks = [t for t in injected if t.get("is_template") is True]
    assert len(template_tasks) == 3
    for t in template_tasks:
        assert t["category"] in ("set_up", "test", "submit")


def test_rule5_does_not_duplicate_existing_categories():
    """
    Rule 5: If Qwen already provided test and set_up, only inject what is missing.
    """
    qwen_tasks = [
        {"category": "set_up", "title": "Set up environment"},
        {"category": "implement", "title": "Implement feature"},
        {"category": "test", "title": "Write unit tests"},
    ]

    injected = _inject_missing_templates(qwen_tasks, repo_name="org/myrepo", contributing_hint="")
    categories = [t["category"] for t in injected]

    # Only 'submit' was missing
    assert categories.count("set_up") == 1
    assert categories.count("test") == 1
    assert categories.count("submit") == 1


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6 & CG-02: Range estimate & Category ordering
# ─────────────────────────────────────────────────────────────────────────────

def test_rule6_ensure_time_range_estimate():
    """
    Rule 6: Estimated times must be a range labelled as an estimate.
    """
    tasks = [
        {"estimated_time": "1 hour"},
        {"estimated_time": "2-3 hours"},
        {"estimated_time": "30–60 min (est.)"},
        {"estimated_time": "unknown"},
        {"estimated_time": ""},
    ]

    processed = _ensure_time_range(tasks)

    for t in processed:
        est = t["estimated_time"]
        assert "(est" in est.lower()
        # Must have a range indicator or be unknown
        assert any(ind in est for ind in ("–", "-", "to", "unknown"))


def test_cg02_fixed_category_ordering():
    """
    CG-02: Tasks must be ordered according to the fixed lifecycle:
    understand -> set_up -> investigate -> plan -> implement -> test -> submit.
    """
    tasks = [
        {"category": "submit", "title": "Submit PR"},
        {"category": "understand", "title": "Read issue"},
        {"category": "implement", "title": "Write code"},
        {"category": "set_up", "title": "Clone repo"},
        {"category": "test", "title": "Run tests"},
        {"category": "investigate", "title": "Locate files"},
        {"category": "plan", "title": "Design solution"},
    ]

    sorted_tasks = _sort_by_category(tasks)
    result_categories = [t["category"] for t in sorted_tasks]

    assert result_categories == CATEGORY_ORDER


# ─────────────────────────────────────────────────────────────────────────────
# End-to-End generate_beginner_plan with Mock Qwen
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_beginner_plan_full_pipeline():
    """
    Full pipeline test verifying all rules integrated together.
    """
    mock_client = MagicMock()
    mock_client.complete_structured = AsyncMock(
        return_value=QwenPlanOutput(
            tasks=[
                {
                    "category": "understand",
                    "requirement_id": "R1",
                    "title": "Understand the error message",
                    "purpose": "Know what to reproduce.",
                    "steps": ["Read issue description", "Check stack trace"],
                    "relevant_files": ["backend/app/main.py", "unreal/file.py"],
                    "estimated_time": "15–30 min",
                    "completion_criteria": "Error can be reproduced locally.",
                },
                {
                    "category": "implement",
                    "requirement_id": "R1",
                    "title": "Fix the error handling",
                    "purpose": "Prevent 500 error on bad input.",
                    "steps": ["Add try/except block in main.py"],
                    "relevant_files": ["backend/app/main.py"],
                    "estimated_time": "1 hour",
                    "completion_criteria": "Input returns 400 instead of 500.",
                },
                {
                    # Invalid requirement_id -> should be rejected!
                    "category": "implement",
                    "requirement_id": "R_FAKE",
                    "title": "Invented task that should be dropped",
                    "purpose": "None",
                    "steps": [],
                },
            ],
            first_approach_note="Focus on verifying the input validation in main.py.",
        )
    )

    req = PlanRequest(
        username="test_contributor",
        issue_url="https://github.com/myorg/myrepo/issues/42",
        requirement_list=[
            {
                "id": "R1",
                "description": "Handle bad input with 400 instead of 500",
                "issue_title": "Fix unhandled 500 on bad JSON",
                "issue_body": "When invalid JSON is sent, server crashes with 500.",
            }
        ],
    )

    known_files = {"backend/app/main.py", "README.md"}

    plan = await generate_beginner_plan(
        request=req,
        known_files=known_files,
        contributing_hint="Check CONTRIBUTING.md",
        qwen_client=mock_client,
    )

    assert isinstance(plan, BeginnerPlan)
    assert plan.status == "ok"
    assert plan.issue_number == 42
    assert plan.issue_title == "Fix unhandled 500 on bad JSON"
    assert len(plan.warnings) >= 1  # Should have warning for rejected R_FAKE

    # Verify task IDs are sequential in code
    for i, t in enumerate(plan.tasks, start=1):
        assert t.task_id == f"T-{i:02d}"

    # Verify R_FAKE was rejected
    req_ids_in_tasks = [t.requirement_id for t in plan.tasks if t.requirement_id]
    assert "R_FAKE" not in req_ids_in_tasks
    assert all(r == "R1" for r in req_ids_in_tasks)

    # Verify template tasks were injected (set_up, test, submit were omitted by Qwen)
    cats = [t.category for t in plan.tasks]
    assert "set_up" in cats
    assert "test" in cats
    assert "submit" in cats

    # Verify fixed order
    cat_indices = [CATEGORY_ORDER.index(t.category) for t in plan.tasks]
    assert cat_indices == sorted(cat_indices)

    # Verify file evidence filtering
    for t in plan.tasks:
        for f in t.relevant_files:
            assert f == "unknown" or f in known_files

    # Verify all estimated times are range estimates
    for t in plan.tasks:
        assert "(est" in t.estimated_time.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Sub-step B: Rules 1, 3, 4, and 5 Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_substep_b_rule1_patch_task_status_success():
    """
    Rule 1: PATCH /beginner/tasks/{id} can update task_status (and blocker_note).
    """
    mock_client = MagicMock()
    mock_client.complete_structured = AsyncMock(
        return_value=QwenPlanOutput(
            tasks=[
                {
                    "category": "implement",
                    "requirement_id": "R1",
                    "title": "Write the core logic",
                    "purpose": "Solve issue.",
                    "estimated_time": "1–2 hours",
                }
            ],
            first_approach_note="First step note.",
        )
    )

    req = PlanRequest(
        username="carol",
        issue_url="https://github.com/myorg/repo/issues/10",
        requirement_list=[{"id": "R1", "description": "Core logic requirement"}],
    )

    await generate_beginner_plan(req, qwen_client=mock_client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Update to IN_PROGRESS
        res1 = await client.patch(
            "/beginner/tasks/T-01",
            json={
                "username": "carol",
                "issue_url": "https://github.com/myorg/repo/issues/10",
                "task_status": "IN_PROGRESS",
            },
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["task"]["task_status"] == "IN_PROGRESS"
        assert data1["completed_count"] == 0

        # 2. Update to BLOCKED with blocker note
        res2 = await client.patch(
            "/beginner/tasks/T-01",
            json={
                "username": "carol",
                "issue_url": "https://github.com/myorg/repo/issues/10",
                "task_status": "BLOCKED",
                "blocker_note": "Missing API credentials",
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["task"]["task_status"] == "BLOCKED"
        assert data2["task"]["blocker_note"] == "Missing API credentials"

        # 3. Update to COMPLETED
        res3 = await client.patch(
            "/beginner/tasks/T-01",
            json={
                "username": "carol",
                "issue_url": "https://github.com/myorg/repo/issues/10",
                "task_status": "COMPLETED",
            },
        )
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["task"]["task_status"] == "COMPLETED"
        assert data3["completed_count"] == 1


@pytest.mark.asyncio
async def test_substep_b_rule1_reject_verification_status_on_patch():
    """
    Rule 1: PATCH /beginner/tasks/{id} may change ONLY task_status.
    Reject any request that tries to set verification_status.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/beginner/tasks/T-01",
            json={
                "username": "carol",
                "issue_url": "https://github.com/myorg/repo/issues/10",
                "verification_status": "VERIFIED",
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "verification_status cannot be modified" in data["detail"]


@pytest.mark.asyncio
async def test_substep_b_rule1_reject_invalid_task_status():
    """
    Rule 1: Reject invalid task_status values.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/beginner/tasks/T-01",
            json={
                "username": "carol",
                "issue_url": "https://github.com/myorg/repo/issues/10",
                "task_status": "DONE_ZOOM_ZOOM",
            },
        )
        assert resp.status_code == 400
        assert "Invalid task_status" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_substep_b_rule3_post_plan_returns_existing_plan():
    """
    Rule 3: POST /beginner/plan must not overwrite a saved plan for the same
    user and issue. Return the existing plan unless regenerate is True.
    """
    mock_client = MagicMock()
    mock_client.complete_structured = AsyncMock(
        return_value=QwenPlanOutput(
            tasks=[
                {
                    "category": "implement",
                    "requirement_id": "R1",
                    "title": "Initial generated task",
                    "purpose": "Initial task.",
                    "estimated_time": "1–2 hours",
                }
            ],
            first_approach_note="First plan approach.",
        )
    )

    req = PlanRequest(
        username="dave",
        issue_url="https://github.com/dave/repo/issues/5",
        requirement_list=[{"id": "R1", "description": "Dave requirement"}],
        regenerate=False,
    )

    # 1. First call generates plan and saves it
    plan1 = await generate_beginner_plan(req, qwen_client=mock_client)
    assert plan1.tasks[0].task_status == "NOT_STARTED"

    # 2. User marks first task as COMPLETED via patch
    from backend.app.services.history_service import update_beginner_task
    update_beginner_task("dave", "https://github.com/dave/repo/issues/5", "T-01", task_status="COMPLETED")

    # Change mock_client return value to confirm it is called only on regenerate
    mock_client.complete_structured = AsyncMock(
        return_value=QwenPlanOutput(
            tasks=[{
                "category": "implement",
                "requirement_id": "R1",
                "title": "OVERWRITTEN_TASK",
                "purpose": "Test task overwrite on regenerate.",
                "estimated_time": "1–2 hours",
            }]
        )
    )

    # 3. Second call with regenerate=False returns existing plan with COMPLETED status
    plan2 = await generate_beginner_plan(req, qwen_client=mock_client)
    mock_client.complete_structured.assert_not_called()
    assert plan2.tasks[0].task_status == "COMPLETED"
    assert plan2.completed_count >= 1

    # 4. Third call with regenerate=True forces regeneration and resets progress
    req_regen = PlanRequest(
        username="dave",
        issue_url="https://github.com/dave/repo/issues/5",
        requirement_list=[{"id": "R1", "description": "Dave requirement"}],
        regenerate=True,
    )
    plan3 = await generate_beginner_plan(req_regen, qwen_client=mock_client)
    mock_client.complete_structured.assert_called_once()
    overwritten = next((t for t in plan3.tasks if "OVERWRITTEN_TASK" in t.title), None)
    assert overwritten is not None
    assert overwritten.task_status == "NOT_STARTED"
    assert plan3.completed_count == 0


def test_substep_b_rule4_weekly_schedule_hours_label_and_growth_speed():
    """
    Rule 4 & Rule 2:
    - Weekly schedule shows 'Planned for X of your Y hours'.
    - Uses casual / steady / fast growth_speed factor.
    """
    from backend.app.services.plan_service import _split_and_schedule_tasks

    tasks = [
        {"task_id": "T-01", "category": "understand", "title": "Task 1", "estimated_time": "1–2 hours (est.)"},
        {"task_id": "T-02", "category": "set_up", "title": "Task 2", "estimated_time": "2–3 hours (est.)"},
        {"task_id": "T-03", "category": "implement", "title": "Task 3", "estimated_time": "2–4 hours (est.)"},
    ]

    # Steady: 8 hours/week * 0.75 = 6.0 target hours
    profile_steady = BeginnerProfileInput(username="eve", hours_per_week=8, growth_speed="steady")
    _, schedule_steady = _split_and_schedule_tasks(tasks, profile_steady)

    assert len(schedule_steady) >= 1
    for s in schedule_steady:
        assert "Planned for" in s["hours_label"]
        assert "of your 6.0 hours" in s["hours_label"]
        assert s["target_hours"] == 6.0

    # Casual: 8 hours/week * 0.5 = 4.0 target hours
    profile_casual = BeginnerProfileInput(username="eve", hours_per_week=8, growth_speed="casual")
    _, schedule_casual = _split_and_schedule_tasks(tasks, profile_casual)
    for s in schedule_casual:
        assert "of your 4.0 hours" in s["hours_label"]
        assert s["target_hours"] == 4.0

    # Fast: 8 hours/week * 1.0 = 8.0 target hours
    profile_fast = BeginnerProfileInput(username="eve", hours_per_week=8, growth_speed="fast")
    _, schedule_fast = _split_and_schedule_tasks(tasks, profile_fast)
    for s in schedule_fast:
        assert "of your 8.0 hours" in s["hours_label"]
        assert s["target_hours"] == 8.0


def test_substep_b_rule4_split_tasks_longer_than_weekly_capacity():
    """
    Rule 4: Tasks longer than a week's capacity are split across weeks.
    """
    from backend.app.services.plan_service import _split_and_schedule_tasks

    # Long task: 10–12 hours (avg 11h). Target hours is 4.0 (8h * casual 0.5)
    tasks = [
        {
            "task_id": "T-01",
            "category": "implement",
            "title": "Very large refactor",
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "estimated_time": "10–12 hours (est.)",
        }
    ]

    profile = BeginnerProfileInput(username="frank", hours_per_week=8, growth_speed="casual")
    split_tasks, schedule = _split_and_schedule_tasks(tasks, profile)

    # 11 hours / 4 hours capacity = 3 parts
    assert len(split_tasks) >= 2
    assert "Part 1 of" in split_tasks[0]["title"]
    assert "Part 2 of" in split_tasks[1]["title"]
    assert split_tasks[0]["week_number"] != split_tasks[-1]["week_number"]

    # Each part has a range estimate
    for st in split_tasks:
        assert "(est" in st["estimated_time"].lower()
        assert "–" in st["estimated_time"]


def test_substep_b_rule5_verification_method_only_from_contributing():
    """
    Rule 5: Show a verification command only if it comes from the repo's
    README or CONTRIBUTING, otherwise show 'unknown'.
    """
    from backend.app.services.plan_service import _validate_verification_methods

    tasks = [
        {"title": "Task with pytest", "verification_method": "pytest tests/test_app.py"},
        {"title": "Task with invented tool", "verification_method": "custom_checker --all"},
    ]

    # When CONTRIBUTING mentions pytest
    hint_with_pytest = "Run `pytest` to execute tests."
    validated_with_evidence = _validate_verification_methods(list(tasks), hint_with_pytest)
    assert validated_with_evidence[0]["verification_method"] == "pytest"
    assert validated_with_evidence[1]["verification_method"] == "unknown"

    # When no CONTRIBUTING evidence exists -> all become 'unknown'
    validated_no_evidence = _validate_verification_methods(list(tasks), "")
    assert validated_no_evidence[0]["verification_method"] == "unknown"
    assert validated_no_evidence[1]["verification_method"] == "unknown"

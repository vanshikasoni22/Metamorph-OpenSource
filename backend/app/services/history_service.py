"""
History & Bookmarking Service
Persists maintainer review comparison runs and contributor saved issues
to PostgreSQL (with SQLite fallback).
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional

from ..database import _USE_SQLALCHEMY, SessionLocal, get_connection
from ..models import MaintainerFetchResponse, ScoreResponse

logger = logging.getLogger("contribo.history_service")


def save_review_report(
    issue_url: str,
    fetch_data: MaintainerFetchResponse,
    score_data: ScoreResponse
) -> Optional[int]:
    """
    Saves a scored PR comparison report to the database.
    Returns the report ID.
    """
    now = time.time()
    top_pr = score_data.candidate_prs[0] if score_data.candidate_prs else None
    top_pr_number = top_pr.pr_number if top_pr else None
    top_score = top_pr.score if top_pr else 0

    # Extract repo from issue url
    parts = issue_url.rstrip("/").split("/")
    repo = f"{parts[-4]}/{parts[-3]}" if len(parts) >= 4 else "unknown/repo"

    full_payload = {
        "issue": fetch_data.issue.model_dump(),
        "score_response": score_data.model_dump(),
        "pull_requests": [pr.model_dump() for pr in fetch_data.pull_requests]
    }
    report_json_str = json.dumps(full_payload)

    if _USE_SQLALCHEMY and SessionLocal:
        try:
            from ..models_db import ReviewReportRecord
            with SessionLocal() as session:
                record = ReviewReportRecord(
                    issue_url=issue_url,
                    issue_title=score_data.issue_title,
                    issue_number=score_data.issue_number,
                    repo=repo,
                    pr_count=len(score_data.candidate_prs),
                    top_pr_number=top_pr_number,
                    top_score=top_score,
                    summary_markdown=score_data.summary_markdown,
                    report_json=report_json_str,
                    created_at=now
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record.id
        except Exception as e:
            logger.warning(f"Failed to save review report via SQLAlchemy: {e}. Falling back to SQLite.")

    # SQLite fallback
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO review_reports (
                    issue_url, issue_title, issue_number, repo,
                    pr_count, top_pr_number, top_score, summary_markdown,
                    report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    issue_url, score_data.issue_title, score_data.issue_number, repo,
                    len(score_data.candidate_prs), top_pr_number, top_score,
                    score_data.summary_markdown, report_json_str, now
                )
            )
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error saving review report to SQLite fallback: {e}")
        return None


def get_review_history(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent maintainer review reports.
    """
    if _USE_SQLALCHEMY and SessionLocal:
        try:
            from ..models_db import ReviewReportRecord
            with SessionLocal() as session:
                records = session.query(ReviewReportRecord)\
                    .order_by(ReviewReportRecord.created_at.desc())\
                    .limit(limit)\
                    .all()

                return [
                    {
                        "id": r.id,
                        "issue_url": r.issue_url,
                        "issue_title": r.issue_title,
                        "issue_number": r.issue_number,
                        "repo": r.repo,
                        "pr_count": r.pr_count,
                        "top_pr_number": r.top_pr_number,
                        "top_score": r.top_score,
                        "created_at": r.created_at,
                        "report": json.loads(r.report_json) if r.report_json else {}
                    }
                    for r in records
                ]
        except Exception as e:
            logger.warning(f"Failed to fetch review history via SQLAlchemy: {e}. Falling back to SQLite.")

    # SQLite fallback
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, issue_url, issue_title, issue_number, repo,
                       pr_count, top_pr_number, top_score, report_json, created_at
                FROM review_reports
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "issue_url": r["issue_url"],
                    "issue_title": r["issue_title"],
                    "issue_number": r["issue_number"],
                    "repo": r["repo"],
                    "pr_count": r["pr_count"],
                    "top_pr_number": r["top_pr_number"],
                    "top_score": r["top_score"],
                    "created_at": r["created_at"],
                    "report": json.loads(r["report_json"]) if r["report_json"] else {}
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Error reading review history from SQLite fallback: {e}")
        return []


def save_beginner_issue(issue_dict: Dict[str, Any], saved_by: str = "anonymous") -> bool:
    """
    Saves / bookmarks an issue for a contributor.
    """
    now = time.time()
    repo = issue_dict.get("repo", "unknown/repo")
    issue_number = issue_dict.get("issue_number", 0)
    title = issue_dict.get("title", "")
    description = issue_dict.get("description", "")
    fit_score = issue_dict.get("fit_score", 0)
    estimated_hours = issue_dict.get("estimated_hours", "")
    url = issue_dict.get("url") or f"https://github.com/{repo}/issues/{issue_number}"
    steps_json = json.dumps(issue_dict.get("implementation_steps", []))
    refs_json = json.dumps(issue_dict.get("codebase_references", []))

    if _USE_SQLALCHEMY and SessionLocal:
        try:
            from ..models_db import SavedIssueRecord
            with SessionLocal() as session:
                existing = session.query(SavedIssueRecord).filter(
                    SavedIssueRecord.saved_by == saved_by,
                    SavedIssueRecord.repo == repo,
                    SavedIssueRecord.issue_number == issue_number
                ).first()
                if not existing:
                    record = SavedIssueRecord(
                        repo=repo,
                        issue_number=issue_number,
                        title=title,
                        description=description,
                        fit_score=fit_score,
                        estimated_hours=estimated_hours,
                        url=url,
                        implementation_steps_json=steps_json,
                        codebase_references_json=refs_json,
                        saved_by=saved_by,
                        created_at=now
                    )
                    session.add(record)
                    session.commit()
            return True
        except Exception as e:
            logger.warning(f"Failed to save issue via SQLAlchemy: {e}. Falling back to SQLite.")

    # SQLite fallback
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO saved_issues (
                    repo, issue_number, title, description,
                    fit_score, estimated_hours, url,
                    implementation_steps_json, codebase_references_json,
                    saved_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo, issue_number, title, description,
                    fit_score, estimated_hours, url,
                    steps_json, refs_json,
                    saved_by, now
                )
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving issue to SQLite: {e}")
        return False


def get_saved_beginner_issues(saved_by: str = "anonymous") -> List[Dict[str, Any]]:
    """
    Returns the list of bookmarked issues for a contributor.
    """
    if _USE_SQLALCHEMY and SessionLocal:
        try:
            from ..models_db import SavedIssueRecord
            with SessionLocal() as session:
                records = session.query(SavedIssueRecord)\
                    .filter(SavedIssueRecord.saved_by == saved_by)\
                    .order_by(SavedIssueRecord.created_at.desc())\
                    .all()

                return [
                    {
                        "id": f"saved-{r.id}",
                        "repo": r.repo,
                        "issue_number": r.issue_number,
                        "title": r.title,
                        "description": r.description,
                        "fit_score": r.fit_score,
                        "estimated_hours": r.estimated_hours,
                        "url": r.url,
                        "implementation_steps": json.loads(r.implementation_steps_json) if r.implementation_steps_json else [],
                        "codebase_references": json.loads(r.codebase_references_json) if r.codebase_references_json else [],
                        "created_at": r.created_at
                    }
                    for r in records
                ]
        except Exception as e:
            logger.warning(f"Failed to fetch saved issues via SQLAlchemy: {e}. Falling back to SQLite.")

    # SQLite fallback
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, repo, issue_number, title, description,
                       fit_score, estimated_hours, url,
                       implementation_steps_json, codebase_references_json, created_at
                FROM saved_issues
                WHERE saved_by = ?
                ORDER BY created_at DESC
                """,
                (saved_by,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": f"saved-{r['id']}",
                    "repo": r["repo"],
                    "issue_number": r["issue_number"],
                    "title": r["title"],
                    "description": r["description"],
                    "fit_score": r["fit_score"],
                    "estimated_hours": r["estimated_hours"],
                    "url": r["url"],
                    "implementation_steps": json.loads(r["implementation_steps_json"]) if r["implementation_steps_json"] else [],
                    "codebase_references": json.loads(r["codebase_references_json"]) if r["codebase_references_json"] else [],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Error reading saved issues from SQLite: {e}")
        return []


def delete_saved_beginner_issue(repo: str, issue_number: int, saved_by: str = "anonymous") -> bool:
    """
    Removes a bookmarked issue.
    """
    if _USE_SQLALCHEMY and SessionLocal:
        try:
            from ..models_db import SavedIssueRecord
            with SessionLocal() as session:
                entry = session.query(SavedIssueRecord).filter(
                    SavedIssueRecord.saved_by == saved_by,
                    SavedIssueRecord.repo == repo,
                    SavedIssueRecord.issue_number == issue_number
                ).first()
                if entry:
                    session.delete(entry)
                    session.commit()
            return True
        except Exception:
            pass

    # SQLite fallback
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM saved_issues WHERE saved_by = ? AND repo = ? AND issue_number = ?",
                (saved_by, repo, issue_number)
            )
            conn.commit()
            return True
    except Exception:
        return False


def save_user_profile(profile_dict: Dict[str, Any]) -> bool:
    """
    Saves or updates a user profile questionnaire in PostgreSQL / SQLite.
    """
    username = profile_dict.get("username", "").strip()
    if not username:
        return False

    now = time.time()
    payload = json.dumps(profile_dict)

    if _USE_SQLALCHEMY and SessionLocal:
        try:
            from ..models_db import UserProfileRecord
            with SessionLocal() as session:
                existing = session.query(UserProfileRecord).filter(
                    UserProfileRecord.username == username
                ).first()
                if existing:
                    existing.profile_json = payload
                    existing.updated_at = now
                else:
                    new_record = UserProfileRecord(
                        username=username,
                        profile_json=payload,
                        updated_at=now
                    )
                    session.add(new_record)
                session.commit()
                return True
        except Exception as e:
            logger.warning(f"Could not save profile via SQLAlchemy: {e}")

    # SQLite fallback
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_profiles (username, profile_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
                """,
                (username, payload, now)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to save profile to SQLite: {e}")
        return False


def get_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a saved user profile questionnaire from PostgreSQL / SQLite.
    """
    clean_user = username.strip()
    if not clean_user:
        return None

    if _USE_SQLALCHEMY and SessionLocal:
        try:
            from ..models_db import UserProfileRecord
            with SessionLocal() as session:
                entry = session.query(UserProfileRecord).filter(
                    UserProfileRecord.username == clean_user
                ).first()
                if entry and entry.profile_json:
                    data = json.loads(entry.profile_json)
                    return data
        except Exception as e:
            logger.warning(f"Could not load profile via SQLAlchemy: {e}")

    # SQLite fallback
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT profile_json FROM user_profiles WHERE username = ?",
                (clean_user,)
            )
            row = cursor.fetchone()
            if row and row["profile_json"]:
                return json.loads(row["profile_json"])
    except Exception as e:
        logger.error(f"Failed to load profile from SQLite: {e}")

    return None


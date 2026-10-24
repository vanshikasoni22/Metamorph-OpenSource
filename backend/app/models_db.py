"""
SQLAlchemy ORM Database Models for Contribo (PostgreSQL & SQLite)
"""

import time
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CacheEntry(Base):
    """
    Stores cached GitHub API responses (issues, PRs, diffs, CI checks)
    with a deterministic SHA256 key and TTL expiration timestamp.
    """
    __tablename__ = "cache_entries"

    cache_key = Column(String(64), primary_key=True, index=True)
    response_json = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False, default=time.time)
    expires_at = Column(Float, nullable=False, index=True)

    def __repr__(self):
        return f"<CacheEntry key={self.cache_key[:8]}... expires_at={self.expires_at}>"


class IssueRecord(Base):
    """
    Persisted GitHub issues tracked or discovered by Contribo.
    """
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(255), nullable=False, index=True)
    issue_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    state = Column(String(50), nullable=False, default="open")
    labels = Column(Text, nullable=True)  # JSON-encoded array or comma-separated
    url = Column(String(500), nullable=False)
    created_at = Column(Float, nullable=False, default=time.time)

    __table_args__ = (
        Index("ix_issues_repo_number", "repo", "issue_number", unique=True),
    )

    def __repr__(self):
        return f"<IssueRecord repo={self.repo} #{self.issue_number}>"


class PullRequestRecord(Base):
    """
    Persisted candidate pull requests inspected by Contribo.
    """
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(255), nullable=False, index=True)
    pr_number = Column(Integer, nullable=False)
    issue_number = Column(Integer, nullable=True, index=True)
    title = Column(String(500), nullable=False)
    author = Column(String(100), nullable=True)
    state = Column(String(50), nullable=False, default="open")
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    changed_files_count = Column(Integer, default=0)
    ci_state = Column(String(50), default="unknown")
    url = Column(String(500), nullable=False)
    created_at = Column(Float, nullable=False, default=time.time)

    __table_args__ = (
        Index("ix_prs_repo_number", "repo", "pr_number", unique=True),
    )

    def __repr__(self):
        return f"<PullRequestRecord repo={self.repo} #{self.pr_number}>"


class ReviewVerdictRecord(Base):
    """
    Persisted maintainer review verdicts, scores, and evidence proof citations.
    """
    __tablename__ = "review_verdicts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_number = Column(Integer, nullable=False, index=True)
    repo = Column(String(255), nullable=True, index=True)
    rank = Column(Integer, default=1)
    score = Column(Integer, default=0)
    verdicts_json = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False, default=time.time)

    def __repr__(self):
        return f"<ReviewVerdictRecord PR #{self.pr_number} rank={self.rank} score={self.score}>"


class ReviewReportRecord(Base):
    """
    Stores a complete maintainer review comparison run for an issue.
    """
    __tablename__ = "review_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_url = Column(String(500), nullable=False, index=True)
    issue_title = Column(String(500), nullable=False)
    issue_number = Column(Integer, nullable=False)
    repo = Column(String(255), nullable=False, index=True)
    pr_count = Column(Integer, default=0)
    top_pr_number = Column(Integer, nullable=True)
    top_score = Column(Integer, default=0)
    summary_markdown = Column(Text, nullable=True)
    report_json = Column(Text, nullable=False)  # Full JSON response of ScoreResponse & PR data
    created_at = Column(Float, nullable=False, default=time.time)

    def __repr__(self):
        return f"<ReviewReportRecord issue={self.repo}#{self.issue_number} top_score={self.top_score}>"


class SavedIssueRecord(Base):
    """
    Saved / bookmarked issues by contributors.
    """
    __tablename__ = "saved_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(255), nullable=False, index=True)
    issue_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    fit_score = Column(Integer, default=0)
    estimated_hours = Column(String(50), nullable=True)
    url = Column(String(500), nullable=False)
    implementation_steps_json = Column(Text, nullable=True)
    codebase_references_json = Column(Text, nullable=True)
    saved_by = Column(String(100), default="anonymous", index=True)
    created_at = Column(Float, nullable=False, default=time.time)

    __table_args__ = (
        Index("ix_saved_issues_user_repo_num", "saved_by", "repo", "issue_number", unique=True),
    )

    def __repr__(self):
        return f"<SavedIssueRecord repo={self.repo} #{self.issue_number} user={self.saved_by}>"


class UserProfileRecord(Base):
    """
    Stores beginner contributor preferences & questionnaire profile.
    """
    __tablename__ = "user_profiles"

    username = Column(String(100), primary_key=True, index=True)
    profile_json = Column(Text, nullable=False)
    updated_at = Column(Float, nullable=False, default=time.time)

    def __repr__(self):
        return f"<UserProfileRecord user={self.username}>"



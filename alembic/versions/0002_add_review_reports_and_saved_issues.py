"""Add review_reports and saved_issues tables

Revision ID: 0002_reports_and_saved_issues
Revises: 0001_initial_postgresql_schema
Create Date: 2026-10-25 03:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_reports_and_saved_issues'
down_revision: Union[str, None] = '0001_initial_postgresql_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. review_reports table
    op.create_table(
        'review_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('issue_url', sa.String(length=500), nullable=False),
        sa.Column('issue_title', sa.String(length=500), nullable=False),
        sa.Column('issue_number', sa.Integer(), nullable=False),
        sa.Column('repo', sa.String(length=255), nullable=False),
        sa.Column('pr_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('top_pr_number', sa.Integer(), nullable=True),
        sa.Column('top_score', sa.Integer(), server_default='0', nullable=True),
        sa.Column('summary_markdown', sa.Text(), nullable=True),
        sa.Column('report_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_reports_issue_url'), 'review_reports', ['issue_url'], unique=False)
    op.create_index(op.f('ix_review_reports_repo'), 'review_reports', ['repo'], unique=False)

    # 2. saved_issues table
    op.create_table(
        'saved_issues',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repo', sa.String(length=255), nullable=False),
        sa.Column('issue_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fit_score', sa.Integer(), server_default='0', nullable=True),
        sa.Column('estimated_hours', sa.String(length=50), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('implementation_steps_json', sa.Text(), nullable=True),
        sa.Column('codebase_references_json', sa.Text(), nullable=True),
        sa.Column('saved_by', sa.String(length=100), server_default='anonymous', nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_saved_issues_user_repo_num', 'saved_issues', ['saved_by', 'repo', 'issue_number'], unique=True)
    op.create_index(op.f('ix_saved_issues_repo'), 'saved_issues', ['repo'], unique=False)
    op.create_index(op.f('ix_saved_issues_saved_by'), 'saved_issues', ['saved_by'], unique=False)


def downgrade() -> None:
    op.drop_table('saved_issues')
    op.drop_table('review_reports')

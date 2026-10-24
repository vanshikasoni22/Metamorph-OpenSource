"""Initial PostgreSQL schema for Contribo

Revision ID: 0001_initial_postgresql_schema
Revises: 
Create Date: 2026-10-25 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_postgresql_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. cache_entries table
    op.create_table(
        'cache_entries',
        sa.Column('cache_key', sa.String(length=64), nullable=False),
        sa.Column('response_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('expires_at', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('cache_key')
    )
    op.create_index(op.f('ix_cache_entries_cache_key'), 'cache_entries', ['cache_key'], unique=False)
    op.create_index(op.f('ix_cache_entries_expires_at'), 'cache_entries', ['expires_at'], unique=False)

    # 2. issues table
    op.create_table(
        'issues',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repo', sa.String(length=255), nullable=False),
        sa.Column('issue_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=50), server_default='open', nullable=False),
        sa.Column('labels', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_issues_repo_number', 'issues', ['repo', 'issue_number'], unique=True)
    op.create_index(op.f('ix_issues_repo'), 'issues', ['repo'], unique=False)

    # 3. pull_requests table
    op.create_table(
        'pull_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repo', sa.String(length=255), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('issue_number', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('author', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), server_default='open', nullable=False),
        sa.Column('additions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('deletions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('changed_files_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('ci_state', sa.String(length=50), server_default='unknown', nullable=True),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prs_repo_number', 'pull_requests', ['repo', 'pr_number'], unique=True)
    op.create_index(op.f('ix_pull_requests_issue_number'), 'pull_requests', ['issue_number'], unique=False)
    op.create_index(op.f('ix_pull_requests_repo'), 'pull_requests', ['repo'], unique=False)

    # 4. review_verdicts table
    op.create_table(
        'review_verdicts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('repo', sa.String(length=255), nullable=True),
        sa.Column('rank', sa.Integer(), server_default='1', nullable=True),
        sa.Column('score', sa.Integer(), server_default='0', nullable=True),
        sa.Column('verdicts_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_verdicts_pr_number'), 'review_verdicts', ['pr_number'], unique=False)
    op.create_index(op.f('ix_review_verdicts_repo'), 'review_verdicts', ['repo'], unique=False)


def downgrade() -> None:
    op.drop_table('review_verdicts')
    op.drop_table('pull_requests')
    op.drop_table('issues')
    op.drop_table('cache_entries')

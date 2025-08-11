"""Merge multiple migration branches

Revision ID: 009_merge_branches
Revises: 007_api_keys_table, add_feature_flags, 006_add_invoice_sequence, 006_add_banking_tables, 2025_01_29_optimization
Create Date: 2025-01-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_merge_branches'
down_revision = (
    '007_api_keys_table',
    'add_feature_flags', 
    '006_add_invoice_sequence',
    '006_add_banking_tables',
    '2025_01_29_optimization'
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    This is a merge migration to consolidate multiple branch heads.
    No schema changes are made here - it just merges the migration paths.
    """
    pass


def downgrade() -> None:
    """
    This is a merge migration to consolidate multiple branch heads.
    No schema changes are made here.
    """
    pass
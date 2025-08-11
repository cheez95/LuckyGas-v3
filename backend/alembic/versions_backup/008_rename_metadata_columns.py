"""Rename metadata columns to notification_metadata

Revision ID: 008_rename_metadata_columns
Revises: 007_add_notification_tables
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_rename_metadata_columns'
down_revision = '007_add_notification_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename metadata columns to avoid SQLAlchemy conflict
    op.alter_column('sms_logs', 'metadata', new_column_name='notification_metadata')
    op.alter_column('notification_logs', 'metadata', new_column_name='notification_metadata')


def downgrade() -> None:
    # Rename back to metadata
    op.alter_column('sms_logs', 'notification_metadata', new_column_name='metadata')
    op.alter_column('notification_logs', 'notification_metadata', new_column_name='metadata')
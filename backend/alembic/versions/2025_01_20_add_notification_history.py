"""Add notification history table

Revision ID: 2025_01_20_notification_history
Revises: 2025_01_20_add_banking_sftp_tables
Create Date: 2025-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_01_20_notification_history'
down_revision = '2025_01_20_add_banking_sftp_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notification_history table
    op.create_table(
        'notification_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('recipient', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='sent'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("type IN ('sms', 'email')", name='check_notification_type'),
        sa.CheckConstraint("status IN ('sent', 'failed')", name='check_notification_status')
    )
    
    # Create indexes for reporting
    op.create_index('idx_notification_type_date', 'notification_history', ['type', 'sent_at'])
    op.create_index('idx_notification_status', 'notification_history', ['status'])
    
    # Optional: Create websocket_connections table for monitoring
    op.create_table(
        'websocket_connections',
        sa.Column('connection_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('connected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_ping', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('connection_id')
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table('websocket_connections')
    op.drop_table('notification_history')
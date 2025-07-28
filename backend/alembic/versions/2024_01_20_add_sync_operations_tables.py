"""Add sync operations tables

Revision ID: add_sync_operations
Revises: previous_revision
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_sync_operations'
down_revision = None  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Create sync_transactions table
    op.create_table('sync_transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'failed', 'conflict', 'retry', 'cancelled', name='syncstatus'), nullable=False),
        sa.Column('operations_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completed_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('atomic', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('stop_on_error', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, server_default='300'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create sync_operations table
    op.create_table('sync_operations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.Enum('customer', 'order', 'delivery', 'product', 'driver', name='entitytype'), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('entity_version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('direction', sa.Enum('to_legacy', 'from_legacy', 'bidirectional', name='syncdirection'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'failed', 'conflict', 'retry', 'cancelled', name='syncstatus'), nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('legacy_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('original_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('resolved_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('conflict_detected', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('conflict_resolution', sa.Enum('newest_wins', 'legacy_wins', 'new_system_wins', 'manual', 'auto_merged', name='conflictresolution'), nullable=True),
        sa.Column('conflict_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('resolved_by', sa.String(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('last_error_at', sa.DateTime(), nullable=True),
        sa.Column('transaction_id', sa.String(), nullable=True),
        sa.Column('depends_on', sa.String(), nullable=True),
        sa.Column('batch_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.Column('sync_duration_ms', sa.Integer(), nullable=True),
        sa.Column('data_size_bytes', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'transaction_id', name='uq_entity_transaction')
    )
    
    # Create indexes
    op.create_index('idx_sync_operations_batch', 'sync_operations', ['batch_id'], unique=False)
    op.create_index('idx_sync_operations_entity', 'sync_operations', ['entity_type', 'entity_id'], unique=False)
    op.create_index('idx_sync_operations_retry', 'sync_operations', ['status', 'next_retry_at'], unique=False)
    op.create_index('idx_sync_operations_status_priority', 'sync_operations', ['status', 'priority'], unique=False)
    op.create_index('idx_sync_operations_transaction', 'sync_operations', ['transaction_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('idx_sync_operations_transaction', table_name='sync_operations')
    op.drop_index('idx_sync_operations_status_priority', table_name='sync_operations')
    op.drop_index('idx_sync_operations_retry', table_name='sync_operations')
    op.drop_index('idx_sync_operations_entity', table_name='sync_operations')
    op.drop_index('idx_sync_operations_batch', table_name='sync_operations')
    
    # Drop tables
    op.drop_table('sync_operations')
    op.drop_table('sync_transactions')
    
    # Drop enums
    sa.Enum('pending', 'in_progress', 'completed', 'failed', 'conflict', 'retry', 'cancelled', name='syncstatus').drop(op.get_bind())
    sa.Enum('to_legacy', 'from_legacy', 'bidirectional', name='syncdirection').drop(op.get_bind())
    sa.Enum('customer', 'order', 'delivery', 'product', 'driver', name='entitytype').drop(op.get_bind())
    sa.Enum('newest_wins', 'legacy_wins', 'new_system_wins', 'manual', 'auto_merged', name='conflictresolution').drop(op.get_bind())
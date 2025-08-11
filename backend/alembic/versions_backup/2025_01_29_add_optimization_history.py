"""Add optimization history table

Revision ID: 2025_01_29_optimization
Revises: add_banking_sftp
Create Date: 2025-01-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2025_01_29_optimization'
down_revision: Union[str, None] = 'add_banking_sftp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create optimization_history table
    op.create_table(
        'optimization_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('optimization_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('request_data', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('optimization_mode', sa.String(), nullable=True),
        sa.Column('total_orders', sa.Integer(), nullable=True),
        sa.Column('total_routes', sa.Integer(), nullable=True),
        sa.Column('total_distance_km', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('savings_percentage', sa.Float(), nullable=True),
        sa.Column('optimization_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_optimization_history_id'), 'optimization_history', ['id'], unique=False)
    op.create_index(op.f('ix_optimization_history_optimization_id'), 'optimization_history', ['optimization_id'], unique=True)
    op.create_index(op.f('ix_optimization_history_created_at'), 'optimization_history', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_optimization_history_created_at'), table_name='optimization_history')
    op.drop_index(op.f('ix_optimization_history_optimization_id'), table_name='optimization_history')
    op.drop_index(op.f('ix_optimization_history_id'), table_name='optimization_history')
    
    # Drop table
    op.drop_table('optimization_history')
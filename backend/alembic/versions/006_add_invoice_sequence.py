"""Add invoice sequence table for Taiwan e-invoice management

Revision ID: 006_add_invoice_sequence
Revises: 005_fix_route_driver_foreign_key
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_invoice_sequence'
down_revision = '005_fix_route_driver_foreign_key'
branch_labels = None
depends_on = None


def upgrade():
    # Create invoice_sequences table
    op.create_table('invoice_sequences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('year_month', sa.String(length=6), nullable=False, comment='YYYYMM format (e.g., 202501)'),
        sa.Column('prefix', sa.String(length=2), nullable=False, comment='Invoice prefix (e.g., AA, AB)'),
        sa.Column('range_start', sa.Integer(), nullable=False, comment='Starting number of allocated range'),
        sa.Column('range_end', sa.Integer(), nullable=False, comment='Ending number of allocated range'),
        sa.Column('current_number', sa.Integer(), nullable=False, comment='Current sequential number'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create unique index for year_month + prefix
    op.create_index(
        'idx_invoice_sequence_unique',
        'invoice_sequences',
        ['year_month', 'prefix'],
        unique=True
    )
    
    # Create index for active sequences
    op.create_index(
        'idx_invoice_sequence_active',
        'invoice_sequences',
        ['is_active', 'year_month']
    )
    
    # Add check constraint to ensure current_number is within range
    op.create_check_constraint(
        'check_current_number_in_range',
        'invoice_sequences',
        'current_number >= range_start AND current_number <= range_end'
    )
    
    # Add check constraint to ensure range is valid
    op.create_check_constraint(
        'check_valid_range',
        'invoice_sequences',
        'range_end > range_start'
    )
    
    # Insert sample invoice sequence for testing (January 2025)
    op.execute("""
        INSERT INTO invoice_sequences (year_month, prefix, range_start, range_end, current_number, notes)
        VALUES 
        ('202501', 'AA', 10000000, 10099999, 10000000, 'Initial allocation for January 2025'),
        ('202501', 'AB', 10000000, 10099999, 10000000, 'Initial allocation for January 2025');
    """)


def downgrade():
    # Drop constraints first
    op.drop_constraint('check_valid_range', 'invoice_sequences', type_='check')
    op.drop_constraint('check_current_number_in_range', 'invoice_sequences', type_='check')
    
    # Drop indexes
    op.drop_index('idx_invoice_sequence_active', table_name='invoice_sequences')
    op.drop_index('idx_invoice_sequence_unique', table_name='invoice_sequences')
    
    # Drop table
    op.drop_table('invoice_sequences')
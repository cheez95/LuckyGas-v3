"""Fix route driver foreign key

Revision ID: 005_fix_route_driver_foreign_key
Revises: 004_add_delivery_history_items
Create Date: 2025-07-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_fix_route_driver_foreign_key'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing foreign key constraint
    op.execute('ALTER TABLE routes DROP CONSTRAINT IF EXISTS routes_driver_id_fkey')
    
    # Add new foreign key constraint pointing to users table
    op.create_foreign_key(
        'routes_driver_id_fkey',
        'routes',
        'users',
        ['driver_id'],
        ['id']
    )
    
    # Drop the drivers table if it exists and is empty
    # First check if there's any data
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT COUNT(*) FROM drivers"))
    count = result.scalar()
    
    if count == 0:
        op.drop_table('drivers')


def downgrade():
    # Create drivers table
    op.create_table('drivers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('employee_id', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Drop the foreign key to users table
    op.drop_constraint('routes_driver_id_fkey', 'routes', type_='foreignkey')
    
    # Add foreign key to drivers table
    op.create_foreign_key(
        'routes_driver_id_fkey',
        'routes',
        'drivers',
        ['driver_id'],
        ['id']
    )
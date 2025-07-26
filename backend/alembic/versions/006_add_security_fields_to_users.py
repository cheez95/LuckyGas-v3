"""Add security fields to users table

Revision ID: 006_security_fields
Revises: 005_fix_route_driver_foreign_key
Create Date: 2024-01-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_security_fields'
down_revision = '005_fix_route_driver_foreign_key'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add security fields to users table
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('two_factor_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    
    # Create index on last_login for performance
    op.create_index('ix_users_last_login', 'users', ['last_login'])
    
    # Set default values for existing rows
    op.execute("UPDATE users SET two_factor_enabled = false WHERE two_factor_enabled IS NULL")
    op.execute("UPDATE users SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL")
    op.execute("UPDATE users SET password_changed_at = created_at WHERE password_changed_at IS NULL")
    
    # Alter columns to set non-nullable where needed
    op.alter_column('users', 'two_factor_enabled', nullable=False)
    op.alter_column('users', 'failed_login_attempts', nullable=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_users_last_login', table_name='users')
    
    # Drop columns
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'two_factor_secret')
    op.drop_column('users', 'two_factor_enabled')
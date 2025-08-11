"""Add feature flag tables

Revision ID: add_feature_flags
Revises: add_sync_operations
Create Date: 2024-01-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_feature_flags'
down_revision = 'add_sync_operations'
branch_labels = None
depends_on = None


def upgrade():
    # Create feature_flags table
    op.create_table('feature_flags',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('type', sa.Enum('boolean', 'percentage', 'variant', 'customer_list', name='featureflagtype'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'scheduled', 'archived', name='featureflagstatus'), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('percentage', sa.Float(), nullable=True, server_default='0'),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.Column('evaluation_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_evaluated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_feature_flags_schedule', 'feature_flags', ['start_date', 'end_date'], unique=False)
    op.create_index('idx_feature_flags_status', 'feature_flags', ['status'], unique=False)
    op.create_index('idx_feature_flags_type', 'feature_flags', ['type'], unique=False)
    op.create_index(op.f('ix_feature_flags_name'), 'feature_flags', ['name'], unique=True)
    
    # Create feature_flag_variants table
    op.create_table('feature_flag_variants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('feature_flag_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('percentage', sa.Float(), nullable=False),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('assignment_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('conversion_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['feature_flag_id'], ['feature_flags.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('feature_flag_id', 'name', name='uq_flag_variant_name')
    )
    op.create_index('idx_variant_flag', 'feature_flag_variants', ['feature_flag_id'], unique=False)
    
    # Create feature_flag_audits table
    op.create_table('feature_flag_audits',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('feature_flag_id', sa.String(), nullable=False),
        sa.Column('action', sa.Enum('created', 'updated', 'deleted', 'activated', 'deactivated', 'customer_added', 'customer_removed', 'percentage_changed', 'variant_changed', 'scheduled', name='auditaction'), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('old_value', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['feature_flag_id'], ['feature_flags.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_action', 'feature_flag_audits', ['action'], unique=False)
    op.create_index('idx_audit_flag_timestamp', 'feature_flag_audits', ['feature_flag_id', 'timestamp'], unique=False)
    op.create_index('idx_audit_user', 'feature_flag_audits', ['user_id'], unique=False)
    
    # Create feature_flag_evaluations table
    op.create_table('feature_flag_evaluations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('feature_flag_id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('variant', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('attributes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('evaluation_time_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['feature_flag_id'], ['feature_flags.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluation_customer', 'feature_flag_evaluations', ['customer_id', 'timestamp'], unique=False)
    op.create_index('idx_evaluation_flag_time', 'feature_flag_evaluations', ['feature_flag_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_feature_flag_evaluations_customer_id'), 'feature_flag_evaluations', ['customer_id'], unique=False)
    op.create_index(op.f('ix_feature_flag_evaluations_feature_flag_id'), 'feature_flag_evaluations', ['feature_flag_id'], unique=False)
    op.create_index(op.f('ix_feature_flag_evaluations_timestamp'), 'feature_flag_evaluations', ['timestamp'], unique=False)
    op.create_index(op.f('ix_feature_flag_evaluations_user_id'), 'feature_flag_evaluations', ['user_id'], unique=False)
    
    # Create association tables
    op.create_table('feature_flag_enabled_customers',
        sa.Column('feature_flag_id', sa.String(), nullable=True),
        sa.Column('customer_id', sa.String(), nullable=True),
        sa.Column('enabled_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('enabled_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['enabled_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['feature_flag_id'], ['feature_flags.id'], ),
        sa.UniqueConstraint('feature_flag_id', 'customer_id', name='uq_flag_customer_enabled')
    )
    
    op.create_table('feature_flag_disabled_customers',
        sa.Column('feature_flag_id', sa.String(), nullable=True),
        sa.Column('customer_id', sa.String(), nullable=True),
        sa.Column('disabled_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('disabled_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['disabled_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['feature_flag_id'], ['feature_flags.id'], ),
        sa.UniqueConstraint('feature_flag_id', 'customer_id', name='uq_flag_customer_disabled')
    )


def downgrade():
    # Drop association tables
    op.drop_table('feature_flag_disabled_customers')
    op.drop_table('feature_flag_enabled_customers')
    
    # Drop indexes and tables
    op.drop_index(op.f('ix_feature_flag_evaluations_user_id'), table_name='feature_flag_evaluations')
    op.drop_index(op.f('ix_feature_flag_evaluations_timestamp'), table_name='feature_flag_evaluations')
    op.drop_index(op.f('ix_feature_flag_evaluations_feature_flag_id'), table_name='feature_flag_evaluations')
    op.drop_index(op.f('ix_feature_flag_evaluations_customer_id'), table_name='feature_flag_evaluations')
    op.drop_index('idx_evaluation_flag_time', table_name='feature_flag_evaluations')
    op.drop_index('idx_evaluation_customer', table_name='feature_flag_evaluations')
    op.drop_table('feature_flag_evaluations')
    
    op.drop_index('idx_audit_user', table_name='feature_flag_audits')
    op.drop_index('idx_audit_flag_timestamp', table_name='feature_flag_audits')
    op.drop_index('idx_audit_action', table_name='feature_flag_audits')
    op.drop_table('feature_flag_audits')
    
    op.drop_index('idx_variant_flag', table_name='feature_flag_variants')
    op.drop_table('feature_flag_variants')
    
    op.drop_index(op.f('ix_feature_flags_name'), table_name='feature_flags')
    op.drop_index('idx_feature_flags_type', table_name='feature_flags')
    op.drop_index('idx_feature_flags_status', table_name='feature_flags')
    op.drop_index('idx_feature_flags_schedule', table_name='feature_flags')
    op.drop_table('feature_flags')
    
    # Drop enums
    sa.Enum('boolean', 'percentage', 'variant', 'customer_list', name='featureflagtype').drop(op.get_bind())
    sa.Enum('active', 'inactive', 'scheduled', 'archived', name='featureflagstatus').drop(op.get_bind())
    sa.Enum('created', 'updated', 'deleted', 'activated', 'deactivated', 'customer_added', 'customer_removed', 'percentage_changed', 'variant_changed', 'scheduled', name='auditaction').drop(op.get_bind())
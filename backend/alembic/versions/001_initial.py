"""Initial schema migration

Revision ID: 001_initial
Create Date: 2025-08-04 05:38:01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial schema"""
    
    # Create enums first
    op.execute("CREATE TYPE auditaction AS ENUM ('LOGIN', 'LOGOUT', 'LOGIN_FAILED', 'PASSWORD_CHANGE', 'PASSWORD_RESET', 'CREATE', 'READ', 'UPDATE', 'DELETE', 'PAYMENT_CREATED', 'PAYMENT_CONFIRMED', 'PAYMENT_FAILED', 'PAYMENT_REFUNDED', 'WEBHOOK_RECEIVED', 'WEBHOOK_PROCESSED', 'WEBHOOK_FAILED', 'API_CALL', 'API_ERROR', 'PERMISSION_GRANTED', 'PERMISSION_REVOKED', 'SECURITY_ALERT', 'SYSTEM_CONFIG_CHANGE', 'BACKUP_CREATED', 'MAINTENANCE_MODE')")
    op.execute("CREATE TYPE conflictresolution AS ENUM ('NEWEST_WINS', 'LEGACY_WINS', 'NEW_SYSTEM_WINS', 'MANUAL', 'AUTO_MERGED')")
    op.execute("CREATE TYPE deliverymethod AS ENUM ('CYLINDER', 'FLOW')")
    op.execute("CREATE TYPE deliverystatus AS ENUM ('PENDING', 'ARRIVED', 'DELIVERED', 'FAILED')")
    op.execute("CREATE TYPE entitytype AS ENUM ('CUSTOMER', 'ORDER', 'DELIVERY', 'PRODUCT', 'DRIVER')")
    op.execute("CREATE TYPE featureflagstatus AS ENUM ('ACTIVE', 'INACTIVE', 'SCHEDULED', 'ARCHIVED')")
    op.execute("CREATE TYPE featureflagtype AS ENUM ('BOOLEAN', 'PERCENTAGE', 'VARIANT', 'CUSTOMER_LIST')")
    op.execute("CREATE TYPE invoicepaymentstatus AS ENUM ('PENDING', 'PARTIAL', 'PAID', 'OVERDUE', 'CANCELLED')")
    op.execute("CREATE TYPE invoicestatus AS ENUM ('DRAFT', 'ISSUED', 'VOID', 'ALLOWANCE', 'CANCELLED')")
    op.execute("CREATE TYPE invoicetype AS ENUM ('B2B', 'B2C', 'DONATION', 'PAPER')")
    op.execute("CREATE TYPE notificationchannel AS ENUM ('SMS', 'EMAIL', 'PUSH', 'IN_APP')")
    op.execute("CREATE TYPE notificationstatus AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'CANCELLED')")
    op.execute("CREATE TYPE orderstatus AS ENUM ('PENDING', 'CONFIRMED', 'ASSIGNED', 'IN_DELIVERY', 'DELIVERED', 'CANCELLED')")
    op.execute("CREATE TYPE paymentbatchstatus AS ENUM ('DRAFT', 'GENERATED', 'UPLOADED', 'PROCESSING', 'RECONCILED', 'FAILED', 'CANCELLED')")
    op.execute("CREATE TYPE paymentmethod AS ENUM ('CASH', 'TRANSFER', 'CHECK', 'CREDIT_CARD', 'MONTHLY')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('UNPAID', 'PAID', 'PARTIAL', 'REFUNDED')")
    op.execute("CREATE TYPE productattribute AS ENUM ('REGULAR', 'HAOYUN', 'PINGAN')")
    op.execute("CREATE TYPE reconciliationstatus AS ENUM ('PENDING', 'MATCHED', 'UNMATCHED', 'MANUAL_REVIEW', 'RESOLVED')")
    op.execute("CREATE TYPE routestatus AS ENUM ('DRAFT', 'PLANNED', 'OPTIMIZED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'PENDING')")
    op.execute("CREATE TYPE smsprovider AS ENUM ('TWILIO', 'CHUNGHWA', 'EVERY8D', 'MITAKE')")
    op.execute("CREATE TYPE stopstatus AS ENUM ('PENDING', 'ARRIVED', 'COMPLETED', 'SKIPPED', 'FAILED')")
    op.execute("CREATE TYPE syncdirection AS ENUM ('TO_LEGACY', 'FROM_LEGACY', 'BIDIRECTIONAL')")
    op.execute("CREATE TYPE syncstatus AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CONFLICT', 'RETRY', 'CANCELLED')")
    op.execute("CREATE TYPE transactionstatus AS ENUM ('PENDING', 'SUCCESS', 'FAILED', 'REJECTED', 'REFUNDED')")
    op.execute("CREATE TYPE userrole AS ENUM ('SUPER_ADMIN', 'MANAGER', 'OFFICE_STAFF', 'DRIVER', 'CUSTOMER')")
    op.execute("CREATE TYPE vehiclestatus AS ENUM ('ACTIVE', 'MAINTENANCE', 'RETIRED')")
    op.execute("CREATE TYPE vehicletype AS ENUM ('TRUCK_SMALL', 'TRUCK_MEDIUM', 'TRUCK_LARGE', 'VAN', 'MOTORCYCLE')")
    op.execute("CREATE TYPE webhookstatus AS ENUM ('RECEIVED', 'PROCESSING', 'PROCESSED', 'FAILED', 'IGNORED')")

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', postgresql.ENUM('SUPER_ADMIN', 'MANAGER', 'OFFICE_STAFF', 'DRIVER', 'CUSTOMER', 
                                         name='userrole', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_code', sa.String(), nullable=False),
        sa.Column('invoice_title', sa.String(), nullable=True),
        sa.Column('short_name', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('area', sa.String(), nullable=True),
        sa.Column('customer_type', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_code')
    )
    
    # Add other tables...
    
    # Create alembic_version table
    op.create_table('alembic_version',
        sa.Column('version_num', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('version_num')
    )

def downgrade():
    """Drop all tables and types"""
    op.drop_table('alembic_version')
    op.drop_table('customers')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS auditaction CASCADE')
    op.execute('DROP TYPE IF EXISTS conflictresolution CASCADE')
    op.execute('DROP TYPE IF EXISTS deliverymethod CASCADE')
    op.execute('DROP TYPE IF EXISTS deliverystatus CASCADE')
    op.execute('DROP TYPE IF EXISTS entitytype CASCADE')
    op.execute('DROP TYPE IF EXISTS featureflagstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS featureflagtype CASCADE')
    op.execute('DROP TYPE IF EXISTS invoicepaymentstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS invoicestatus CASCADE')
    op.execute('DROP TYPE IF EXISTS invoicetype CASCADE')
    op.execute('DROP TYPE IF EXISTS notificationchannel CASCADE')
    op.execute('DROP TYPE IF EXISTS notificationstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS orderstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS paymentbatchstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS paymentmethod CASCADE')
    op.execute('DROP TYPE IF EXISTS paymentstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS productattribute CASCADE')
    op.execute('DROP TYPE IF EXISTS reconciliationstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS routestatus CASCADE')
    op.execute('DROP TYPE IF EXISTS smsprovider CASCADE')
    op.execute('DROP TYPE IF EXISTS stopstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS syncdirection CASCADE')
    op.execute('DROP TYPE IF EXISTS syncstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS transactionstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS userrole CASCADE')
    op.execute('DROP TYPE IF EXISTS vehiclestatus CASCADE')
    op.execute('DROP TYPE IF EXISTS vehicletype CASCADE')
    op.execute('DROP TYPE IF EXISTS webhookstatus CASCADE')

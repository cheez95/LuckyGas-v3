"""Add banking tables for payment processing

Revision ID: 006_add_banking_tables
Revises: 005_fix_route_driver_foreign_key
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_banking_tables'
down_revision = '005_fix_route_driver_foreign_key'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bank_configurations table
    op.create_table('bank_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bank_code', sa.String(length=10), nullable=False),
        sa.Column('bank_name', sa.String(length=100), nullable=False),
        sa.Column('sftp_host', sa.String(length=255), nullable=False),
        sa.Column('sftp_port', sa.Integer(), nullable=True),
        sa.Column('sftp_username', sa.String(length=100), nullable=False),
        sa.Column('sftp_password', sa.String(length=255), nullable=False),
        sa.Column('sftp_private_key', sa.Text(), nullable=True),
        sa.Column('upload_path', sa.String(length=500), nullable=False),
        sa.Column('download_path', sa.String(length=500), nullable=False),
        sa.Column('archive_path', sa.String(length=500), nullable=True),
        sa.Column('file_format', sa.String(length=20), nullable=False),
        sa.Column('encoding', sa.String(length=20), nullable=True),
        sa.Column('delimiter', sa.String(length=5), nullable=True),
        sa.Column('payment_file_pattern', sa.String(length=100), nullable=True),
        sa.Column('reconciliation_file_pattern', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('cutoff_time', sa.String(length=5), nullable=True),
        sa.Column('retry_attempts', sa.Integer(), nullable=True),
        sa.Column('retry_delay_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bank_configurations_bank_code'), 'bank_configurations', ['bank_code'], unique=True)
    
    # Create payment_batches table
    op.create_table('payment_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_number', sa.String(length=50), nullable=False),
        sa.Column('bank_code', sa.String(length=10), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_content', sa.Text(), nullable=True),
        sa.Column('file_format', sa.String(length=20), nullable=False),
        sa.Column('total_transactions', sa.Integer(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('processing_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'GENERATED', 'UPLOADED', 'PROCESSING', 'RECONCILED', 'FAILED', 'CANCELLED', name='paymentbatchstatus'), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('reconciled_at', sa.DateTime(), nullable=True),
        sa.Column('sftp_upload_path', sa.String(length=500), nullable=True),
        sa.Column('sftp_download_path', sa.String(length=500), nullable=True),
        sa.Column('reconciliation_file_name', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_batches_batch_number'), 'payment_batches', ['batch_number'], unique=True)
    op.create_index(op.f('ix_payment_batches_bank_code'), 'payment_batches', ['bank_code'], unique=False)
    op.create_index(op.f('ix_payment_batches_status'), 'payment_batches', ['status'], unique=False)
    op.create_index('idx_payment_batch_date_bank', 'payment_batches', ['processing_date', 'bank_code'], unique=False)
    op.create_index('idx_payment_batch_status_date', 'payment_batches', ['status', 'processing_date'], unique=False)
    
    # Create payment_transactions table
    op.create_table('payment_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(length=50), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('account_number', sa.String(length=20), nullable=False),
        sa.Column('account_holder', sa.String(length=100), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'SUCCESS', 'FAILED', 'REJECTED', 'REFUNDED', name='transactionstatus'), nullable=False),
        sa.Column('bank_reference', sa.String(length=50), nullable=True),
        sa.Column('bank_response_code', sa.String(length=10), nullable=True),
        sa.Column('bank_response_message', sa.Text(), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(), nullable=False),
        sa.Column('processed_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['payment_batches.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_transactions_batch_id'), 'payment_transactions', ['batch_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_customer_id'), 'payment_transactions', ['customer_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_invoice_id'), 'payment_transactions', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_status'), 'payment_transactions', ['status'], unique=False)
    op.create_index(op.f('ix_payment_transactions_transaction_id'), 'payment_transactions', ['transaction_id'], unique=True)
    op.create_index('idx_payment_trans_customer_date', 'payment_transactions', ['customer_id', 'scheduled_date'], unique=False)
    op.create_index('idx_payment_trans_status_date', 'payment_transactions', ['status', 'scheduled_date'], unique=False)
    
    # Create reconciliation_logs table
    op.create_table('reconciliation_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_received_at', sa.DateTime(), nullable=False),
        sa.Column('file_content', sa.Text(), nullable=True),
        sa.Column('total_records', sa.Integer(), nullable=True),
        sa.Column('matched_records', sa.Integer(), nullable=True),
        sa.Column('unmatched_records', sa.Integer(), nullable=True),
        sa.Column('failed_records', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'MATCHED', 'UNMATCHED', 'MANUAL_REVIEW', 'RESOLVED', name='reconciliationstatus'), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('manual_review_notes', sa.Text(), nullable=True),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['payment_batches.id'], ),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reconciliation_logs_batch_id'), 'reconciliation_logs', ['batch_id'], unique=False)
    op.create_index(op.f('ix_reconciliation_logs_status'), 'reconciliation_logs', ['status'], unique=False)
    op.create_index('idx_reconciliation_status_date', 'reconciliation_logs', ['status', 'file_received_at'], unique=False)
    
    # Add bank account fields to customers table if they don't exist
    with op.batch_alter_table('customers') as batch_op:
        # Check if columns exist before adding
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_columns = [col['name'] for col in inspector.get_columns('customers')]
        
        if 'payment_method' not in existing_columns:
            batch_op.add_column(sa.Column('payment_method', sa.String(length=50), nullable=True))
        if 'bank_code' not in existing_columns:
            batch_op.add_column(sa.Column('bank_code', sa.String(length=10), nullable=True))
        if 'bank_account_number' not in existing_columns:
            batch_op.add_column(sa.Column('bank_account_number', sa.String(length=20), nullable=True))
        if 'bank_account_holder' not in existing_columns:
            batch_op.add_column(sa.Column('bank_account_holder', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove bank account fields from customers table
    with op.batch_alter_table('customers') as batch_op:
        # Check if columns exist before dropping
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_columns = [col['name'] for col in inspector.get_columns('customers')]
        
        if 'bank_account_holder' in existing_columns:
            batch_op.drop_column('bank_account_holder')
        if 'bank_account_number' in existing_columns:
            batch_op.drop_column('bank_account_number')
        if 'bank_code' in existing_columns:
            batch_op.drop_column('bank_code')
        if 'payment_method' in existing_columns:
            batch_op.drop_column('payment_method')
    
    # Drop tables in reverse order
    op.drop_index('idx_reconciliation_status_date', table_name='reconciliation_logs')
    op.drop_index(op.f('ix_reconciliation_logs_status'), table_name='reconciliation_logs')
    op.drop_index(op.f('ix_reconciliation_logs_batch_id'), table_name='reconciliation_logs')
    op.drop_table('reconciliation_logs')
    
    op.drop_index('idx_payment_trans_status_date', table_name='payment_transactions')
    op.drop_index('idx_payment_trans_customer_date', table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_transaction_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_status'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_invoice_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_customer_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_batch_id'), table_name='payment_transactions')
    op.drop_table('payment_transactions')
    
    op.drop_index('idx_payment_batch_status_date', table_name='payment_batches')
    op.drop_index('idx_payment_batch_date_bank', table_name='payment_batches')
    op.drop_index(op.f('ix_payment_batches_status'), table_name='payment_batches')
    op.drop_index(op.f('ix_payment_batches_bank_code'), table_name='payment_batches')
    op.drop_index(op.f('ix_payment_batches_batch_number'), table_name='payment_batches')
    op.drop_table('payment_batches')
    
    op.drop_index(op.f('ix_bank_configurations_bank_code'), table_name='bank_configurations')
    op.drop_table('bank_configurations')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS paymentbatchstatus")
    op.execute("DROP TYPE IF EXISTS transactionstatus")
    op.execute("DROP TYPE IF EXISTS reconciliationstatus")
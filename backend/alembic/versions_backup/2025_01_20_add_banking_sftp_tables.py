"""Add banking SFTP automation tables

Revision ID: add_banking_sftp
Revises: 2024_01_20_add_sync_operations_tables
Create Date: 2025-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_01_20_add_banking_sftp_tables'
down_revision = 'add_sms_tables_2024_01_20'
branch_labels = None
depends_on = None


def upgrade():
    """Add banking SFTP automation tables and initial configuration."""
    
    # Add new columns to bank_configurations table if they don't exist
    op.add_column('bank_configurations', 
        sa.Column('file_checksum', sa.String(64), nullable=True),
        if_not_exists=True
    )
    
    # Create transfer_logs table for SFTP transfer history
    op.create_table('transfer_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bank_code', sa.String(10), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),  # upload/download
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('local_path', sa.String(500), nullable=True),
        sa.Column('remote_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('encryption_used', sa.Boolean(), default=True),
        sa.Column('transfer_started_at', sa.DateTime(), nullable=False),
        sa.Column('transfer_completed_at', sa.DateTime(), nullable=True),
        sa.Column('transfer_duration', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),  # success/failed/retry
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['batch_id'], ['payment_batches.id'], ondelete='SET NULL'),
        sa.Index('idx_transfer_log_bank_date', 'bank_code', 'transfer_started_at'),
        sa.Index('idx_transfer_log_status', 'status', 'created_at')
    )
    
    # Create sftp_health_checks table
    op.create_table('sftp_health_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bank_code', sa.String(10), nullable=False),
        sa.Column('check_timestamp', sa.DateTime(), nullable=False),
        sa.Column('connection_status', sa.String(20), nullable=False),  # connected/failed/timeout
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('circuit_breaker_state', sa.String(20), nullable=True),  # closed/open/half-open
        sa.Column('connection_pool_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_health_check_bank_time', 'bank_code', 'check_timestamp')
    )
    
    # Create encryption_keys table for PGP key management
    op.create_table('encryption_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bank_code', sa.String(10), nullable=False),
        sa.Column('key_type', sa.String(20), nullable=False),  # public/private
        sa.Column('key_id', sa.String(40), nullable=True),
        sa.Column('fingerprint', sa.String(40), nullable=True),
        sa.Column('algorithm', sa.String(20), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=False),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bank_code', 'key_type', 'key_id', name='uq_bank_key'),
        sa.Index('idx_encryption_key_active', 'bank_code', 'is_active')
    )
    
    # Insert default bank configurations for Taiwan banks
    op.execute("""
        INSERT INTO bank_configurations (
            bank_code, bank_name, sftp_host, sftp_port, sftp_username, sftp_password,
            upload_path, download_path, archive_path,
            file_format, encoding, delimiter,
            payment_file_pattern, reconciliation_file_pattern,
            is_active, cutoff_time, retry_attempts, retry_delay_minutes,
            created_at, updated_at
        ) VALUES
        ('mega', '兆豐銀行', 'sftp.megabank.com.tw', 22, 'luckygas', 'temp_password',
         '/incoming/payments', '/outgoing/reconciliation', '/archive',
         'fixed_width', 'Big5', NULL,
         'PAY_{YYYYMMDD}_{BATCH}.txt', 'REC_{YYYYMMDD}*.txt',
         true, '15:30', 3, 30, NOW(), NOW()),
         
        ('ctbc', '中國信託', 'sftp.ctbcbank.com', 22, 'luckygas', 'temp_password',
         '/upload/ach', '/download/recon', '/archive',
         'fixed_width', 'Big5', NULL,
         'CTBC_PAY_{YYYYMMDD}_{BATCH}.DAT', 'CTBC_REC_{YYYYMMDD}*.DAT',
         true, '16:00', 3, 30, NOW(), NOW()),
         
        ('esun', '玉山銀行', 'sftp.esunbank.com.tw', 22, 'luckygas', 'temp_password',
         '/payment/upload', '/recon/download', '/processed',
         'csv', 'UTF-8', ',',
         'ESUN_PAYMENT_{YYYYMMDD}_{BATCH}.csv', 'ESUN_RECON_{YYYYMMDD}*.csv',
         true, '15:00', 3, 30, NOW(), NOW()),
         
        ('first', '第一銀行', 'sftp.firstbank.com.tw', 22, 'luckygas', 'temp_password',
         '/ach/incoming', '/ach/outgoing', '/ach/archive',
         'fixed_width', 'Big5', NULL,
         'FIRST_ACH_{YYYYMMDD}_{BATCH}.txt', 'FIRST_RET_{YYYYMMDD}*.txt',
         true, '15:30', 3, 30, NOW(), NOW()),
         
        ('taishin', '台新銀行', 'sftp.taishinbank.com.tw', 22, 'luckygas', 'temp_password',
         '/luckygas/payment', '/luckygas/reconcile', '/luckygas/archive',
         'fixed_width', 'Big5', NULL,
         'TSB_PAY_{BATCH}_{YYYYMMDD}.txt', 'TSB_REC_{YYYYMMDD}*.txt',
         true, '16:30', 3, 30, NOW(), NOW())
        ON CONFLICT (bank_code) DO NOTHING;
    """)
    
    # Add indexes to payment_batches table for better performance
    op.create_index('idx_payment_batch_checksum', 'payment_batches', ['file_checksum'], if_not_exists=True)
    
    # Add column to payment_transactions for tracking retries
    op.add_column('payment_transactions',
        sa.Column('last_retry_at', sa.DateTime(), nullable=True),
        if_not_exists=True
    )
    op.add_column('payment_transactions',
        sa.Column('retry_count', sa.Integer(), default=0),
        if_not_exists=True
    )


def downgrade():
    """Remove banking SFTP automation tables."""
    
    # Drop new columns from payment_transactions
    op.drop_column('payment_transactions', 'retry_count', if_exists=True)
    op.drop_column('payment_transactions', 'last_retry_at', if_exists=True)
    
    # Drop indexes
    op.drop_index('idx_payment_batch_checksum', 'payment_batches', if_exists=True)
    
    # Drop tables
    op.drop_table('encryption_keys', if_exists=True)
    op.drop_table('sftp_health_checks', if_exists=True)
    op.drop_table('transfer_logs', if_exists=True)
    
    # Drop column from bank_configurations
    op.drop_column('bank_configurations', 'file_checksum', if_exists=True)
    
    # Delete default bank configurations
    op.execute("""
        DELETE FROM bank_configurations 
        WHERE bank_code IN ('mega', 'ctbc', 'esun', 'first', 'taishin')
    """)
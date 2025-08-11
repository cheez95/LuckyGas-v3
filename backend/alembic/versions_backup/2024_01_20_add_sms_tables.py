"""Add SMS notification tables

Revision ID: add_sms_tables_2024_01_20
Revises: 2024_01_20_add_sync_operations_tables
Create Date: 2024-01-20 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'add_sms_tables_2024_01_20'
down_revision = 'add_sync_operations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE notificationstatus AS ENUM ('pending', 'sent', 'delivered', 'failed', 'cancelled')")
    op.execute("CREATE TYPE smsprovider AS ENUM ('twilio', 'chunghwa', 'every8d', 'mitake')")
    op.execute("CREATE TYPE notificationchannel AS ENUM ('sms', 'email', 'push', 'in_app')")
    
    # Create sms_logs table
    op.create_table(
        'sms_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('recipient', sa.String(50), nullable=False),
        sa.Column('sender_id', sa.String(50), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=True),
        sa.Column('provider', postgresql.ENUM('twilio', 'chunghwa', 'every8d', 'mitake', name='smsprovider'), nullable=False),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'sent', 'delivered', 'failed', 'cancelled', name='notificationstatus'), nullable=False, server_default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('segments', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('unicode_message', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notification_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for sms_logs
    op.create_index('idx_sms_logs_recipient', 'sms_logs', ['recipient'])
    op.create_index('idx_sms_logs_status', 'sms_logs', ['status'])
    op.create_index('idx_sms_logs_created_at', 'sms_logs', ['created_at'])
    op.create_index('idx_sms_logs_status_created', 'sms_logs', ['status', 'created_at'])
    op.create_index('idx_sms_logs_provider_status', 'sms_logs', ['provider', 'status'])
    
    # Create sms_templates table
    op.create_table(
        'sms_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('language', sa.String(10), nullable=False, server_default='zh-TW'),
        sa.Column('variant', sa.String(10), nullable=True, server_default='A'),
        sa.Column('weight', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('sent_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('delivered_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('click_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('effectiveness_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', 'variant', name='uq_sms_templates_code_variant')
    )
    
    # Create indexes for sms_templates
    op.create_index('idx_sms_templates_code', 'sms_templates', ['code'])
    op.create_index('idx_sms_templates_code_active', 'sms_templates', ['code', 'is_active'])
    op.create_index('idx_sms_templates_code_variant', 'sms_templates', ['code', 'variant'])
    
    # Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('channel', postgresql.ENUM('sms', 'email', 'push', 'in_app', name='notificationchannel'), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'sent', 'delivered', 'failed', 'cancelled', name='notificationstatus'), nullable=False, server_default='pending'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notification_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for notification_logs
    op.create_index('idx_notification_logs_recipient', 'notification_logs', ['recipient'])
    op.create_index('idx_notification_logs_channel', 'notification_logs', ['channel'])
    op.create_index('idx_notification_logs_status', 'notification_logs', ['status'])
    op.create_index('idx_notification_logs_user_id', 'notification_logs', ['user_id'])
    op.create_index('idx_notification_logs_order_id', 'notification_logs', ['order_id'])
    op.create_index('idx_notification_logs_user_created', 'notification_logs', ['user_id', 'created_at'])
    op.create_index('idx_notification_logs_channel_status', 'notification_logs', ['channel', 'status'])
    
    # Create provider_configs table
    op.create_table(
        'provider_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('provider', postgresql.ENUM('twilio', 'chunghwa', 'every8d', 'mitake', name='smsprovider'), nullable=False),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.Column('daily_limit', sa.Integer(), nullable=True),
        sa.Column('cost_per_message', sa.Float(), nullable=True),
        sa.Column('cost_per_segment', sa.Float(), nullable=True),
        sa.Column('total_sent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_failed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', name='uq_provider_configs_provider')
    )
    
    # Insert default SMS templates
    op.execute("""
        INSERT INTO sms_templates (id, code, name, content, variant, weight) VALUES
        (gen_random_uuid(), 'order_confirmation', '訂單確認', '【幸福氣】訂單確認：您的訂單 {order_id} 已確認，預計送達時間 {delivery_time}', 'A', 50),
        (gen_random_uuid(), 'order_confirmation', '訂單確認（簡潔版）', '【幸福氣】訂單 {order_id} 確認，預計 {delivery_time} 送達', 'B', 50),
        (gen_random_uuid(), 'out_for_delivery', '配送中通知', '【幸福氣】配送通知：您的訂單 {order_id} 正在配送中，司機 {driver_name} 將在 {eta} 分鐘內送達', 'A', 100),
        (gen_random_uuid(), 'delivery_completed', '配送完成', '【幸福氣】配送完成：您的訂單 {order_id} 已送達，感謝您的訂購！', 'A', 100),
        (gen_random_uuid(), 'payment_reminder', '付款提醒', '【幸福氣】付款提醒：您有待付款訂單 {order_id}，金額 NT${amount}，請儘快完成付款', 'A', 100)
    """)
    
    # Insert default provider configurations
    op.execute("""
        INSERT INTO provider_configs (id, provider, config, priority, rate_limit, cost_per_message) VALUES
        (gen_random_uuid(), 'twilio', '{}', 100, 60, 0.5),
        (gen_random_uuid(), 'chunghwa', '{}', 90, 100, 0.7)
    """)


def downgrade() -> None:
    # Drop tables
    op.drop_table('provider_configs')
    op.drop_table('notification_logs')
    op.drop_table('sms_templates')
    op.drop_table('sms_logs')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS notificationchannel")
    op.execute("DROP TYPE IF EXISTS smsprovider")
    op.execute("DROP TYPE IF EXISTS notificationstatus")
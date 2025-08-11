"""Add notification tables

Revision ID: 007_add_notification_tables
Revises: 005_fix_route_driver_foreign_key
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '007_add_notification_tables'
down_revision = '005_fix_route_driver_foreign_key'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create SMS provider enum
    op.execute("""
        CREATE TYPE smsprovider AS ENUM ('twilio', 'every8d', 'mitake');
    """)
    
    # Create notification status enum
    op.execute("""
        CREATE TYPE notificationstatus AS ENUM ('pending', 'sent', 'delivered', 'failed', 'cancelled');
    """)
    
    # Create notification channel enum
    op.execute("""
        CREATE TYPE notificationchannel AS ENUM ('sms', 'email', 'push', 'in_app');
    """)
    
    # Create provider_configs table
    op.create_table('provider_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('provider', postgresql.ENUM('twilio', 'every8d', 'mitake', name='smsprovider'), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=0),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.Column('daily_limit', sa.Integer(), nullable=True),
        sa.Column('cost_per_message', sa.Float(), nullable=True),
        sa.Column('cost_per_segment', sa.Float(), nullable=True),
        sa.Column('total_sent', sa.Integer(), nullable=True, default=0),
        sa.Column('total_failed', sa.Integer(), nullable=True, default=0),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider')
    )
    
    # Create sms_templates table
    op.create_table('sms_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('language', sa.String(10), nullable=False, default='zh-TW'),
        sa.Column('variant', sa.String(10), nullable=True, default='A'),
        sa.Column('weight', sa.Integer(), nullable=True, default=100),
        sa.Column('sent_count', sa.Integer(), nullable=True, default=0),
        sa.Column('delivered_count', sa.Integer(), nullable=True, default=0),
        sa.Column('click_count', sa.Integer(), nullable=True, default=0),
        sa.Column('effectiveness_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sms_templates_code_active', 'sms_templates', ['code', 'is_active'])
    op.create_index('idx_sms_templates_code_variant', 'sms_templates', ['code', 'variant'])
    op.create_index('idx_sms_templates_code', 'sms_templates', ['code'])
    
    # Create sms_logs table
    op.create_table('sms_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('recipient', sa.String(50), nullable=False),
        sa.Column('sender_id', sa.String(50), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=True),
        sa.Column('provider', postgresql.ENUM('twilio', 'every8d', 'mitake', name='smsprovider'), nullable=False),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'sent', 'delivered', 'failed', 'cancelled', name='notificationstatus'), nullable=False, default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('segments', sa.Integer(), nullable=True, default=1),
        sa.Column('unicode_message', sa.Boolean(), nullable=True, default=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sms_logs_recipient', 'sms_logs', ['recipient'])
    op.create_index('idx_sms_logs_status', 'sms_logs', ['status'])
    op.create_index('idx_sms_logs_created_at', 'sms_logs', ['created_at'])
    op.create_index('idx_sms_logs_status_created', 'sms_logs', ['status', 'created_at'])
    op.create_index('idx_sms_logs_provider_status', 'sms_logs', ['provider', 'status'])
    
    # Create notification_logs table
    op.create_table('notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('channel', postgresql.ENUM('sms', 'email', 'push', 'in_app', name='notificationchannel'), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'sent', 'delivered', 'failed', 'cancelled', name='notificationstatus'), nullable=False, default='pending'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notification_logs_channel', 'notification_logs', ['channel'])
    op.create_index('idx_notification_logs_recipient', 'notification_logs', ['recipient'])
    op.create_index('idx_notification_logs_status', 'notification_logs', ['status'])
    op.create_index('idx_notification_logs_user_id', 'notification_logs', ['user_id'])
    op.create_index('idx_notification_logs_order_id', 'notification_logs', ['order_id'])
    op.create_index('idx_notification_logs_user_created', 'notification_logs', ['user_id', 'created_at'])
    op.create_index('idx_notification_logs_channel_status', 'notification_logs', ['channel', 'status'])
    
    # Insert default SMS templates
    op.execute("""
        INSERT INTO sms_templates (id, code, name, content, language, is_active)
        VALUES 
        (gen_random_uuid(), 'order_confirmation', '訂單確認', '【幸福氣】您的訂單 {order_number} 已確認，預計配送時間：{delivery_time}', 'zh-TW', true),
        (gen_random_uuid(), 'delivery_on_way', '配送中', '【幸福氣】您的瓦斯正在配送中，司機 {driver_name} 預計 {eta} 分鐘後到達', 'zh-TW', true),
        (gen_random_uuid(), 'delivery_arrived', '已到達', '【幸福氣】配送員已到達您的地址，請準備接收瓦斯', 'zh-TW', true),
        (gen_random_uuid(), 'delivery_completed', '配送完成', '【幸福氣】您的訂單 {order_number} 已送達完成，感謝您的訂購！', 'zh-TW', true),
        (gen_random_uuid(), 'order_cancelled', '訂單取消', '【幸福氣】您的訂單 {order_number} 已取消，如有疑問請聯繫客服', 'zh-TW', true),
        (gen_random_uuid(), 'payment_reminder', '付款提醒', '【幸福氣】提醒您，訂單 {order_number} 尚有 NT${amount} 待付款', 'zh-TW', true);
    """)


def downgrade() -> None:
    # Drop tables
    op.drop_table('notification_logs')
    op.drop_table('sms_logs')
    op.drop_table('sms_templates')
    op.drop_table('provider_configs')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS notificationchannel')
    op.execute('DROP TYPE IF EXISTS notificationstatus')
    op.execute('DROP TYPE IF EXISTS smsprovider')
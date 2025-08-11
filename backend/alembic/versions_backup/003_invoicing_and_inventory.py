"""Create invoicing and inventory tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', postgresql.ENUM('draft', 'sent', 'paid', 'partial', 'overdue', 'cancelled', name='invoicestatus'), nullable=False),
        sa.Column('type', postgresql.ENUM('standard', 'recurring', 'deposit', 'credit_note', name='invoicetype'), nullable=False),
        sa.Column('payment_status', postgresql.ENUM('pending', 'partial', 'paid', 'overdue', name='invoicepaymentstatus'), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('paid_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=True)
    op.create_index(op.f('ix_invoices_customer_id'), 'invoices', ['customer_id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_date'), 'invoices', ['invoice_date'], unique=False)
    
    # Create invoice_items table
    op.create_table('invoice_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['gas_products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_items_invoice_id'), 'invoice_items', ['invoice_id'], unique=False)
    
    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_number', sa.String(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_method', postgresql.ENUM('cash', 'check', 'bank_transfer', 'mobile_payment', 'credit_card', name='paymentmethod'), nullable=False),
        sa.Column('reference_number', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_payment_number'), 'payments', ['payment_number'], unique=True)
    op.create_index(op.f('ix_payments_invoice_id'), 'payments', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payments_payment_date'), 'payments', ['payment_date'], unique=False)
    
    # Create credit_notes table
    op.create_table('credit_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('credit_note_number', sa.String(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_credit_notes_credit_note_number'), 'credit_notes', ['credit_note_number'], unique=True)
    op.create_index(op.f('ix_credit_notes_customer_id'), 'credit_notes', ['customer_id'], unique=False)
    
    # Create customer_inventory table
    op.create_table('customer_inventory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_delivery_date', sa.Date(), nullable=True),
        sa.Column('average_consumption_days', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['gas_products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_inventory_customer_id'), 'customer_inventory', ['customer_id'], unique=False)
    op.create_index(op.f('ix_customer_inventory_product_id'), 'customer_inventory', ['product_id'], unique=False)
    
    # Create prediction_batch table
    op.create_table('prediction_batch',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_date', sa.Date(), nullable=False),
        sa.Column('model_version', sa.String(), nullable=False),
        sa.Column('total_predictions', sa.Integer(), nullable=False),
        sa.Column('avg_confidence_score', sa.Float(), nullable=True),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_batch_batch_date'), 'prediction_batch', ['batch_date'], unique=False)
    
    # Create route_deliveries table (link between routes and deliveries)
    op.create_table('route_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('delivery_id', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled', name='deliverystatus'), nullable=False),
        sa.Column('arrival_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('driver_notes', sa.Text(), nullable=True),
        sa.Column('customer_signature', sa.String(), nullable=True),
        sa.Column('photo_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['delivery_id'], ['deliveries.id'], ),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_route_deliveries_route_id'), 'route_deliveries', ['route_id'], unique=False)
    op.create_index(op.f('ix_route_deliveries_delivery_id'), 'route_deliveries', ['delivery_id'], unique=False)
    
    # Create delivery_status_history table
    op.create_table('delivery_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('delivery_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled', name='deliverystatus'), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['delivery_id'], ['deliveries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_status_history_delivery_id'), 'delivery_status_history', ['delivery_id'], unique=False)
    
    # Create delivery_history table for historical records
    op.create_table('delivery_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('transaction_time', sa.String(), nullable=True),
        sa.Column('salesperson', sa.String(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('customer_code', sa.String(), nullable=False),
        sa.Column('qty_50kg', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_ying20', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_ying16', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_20kg', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_16kg', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_10kg', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_4kg', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_haoyun20', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_haoyun16', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_pingantong10', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qty_xingfuwan4', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('flow_50kg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('flow_20kg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('flow_16kg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('flow_haoyun20kg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('flow_haoyun16kg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('total_cylinders', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_weight_kg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('source_file', sa.String(), nullable=True),
        sa.Column('source_sheet', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_history_customer_id'), 'delivery_history', ['customer_id'], unique=False)
    op.create_index(op.f('ix_delivery_history_transaction_date'), 'delivery_history', ['transaction_date'], unique=False)
    op.create_index(op.f('ix_delivery_history_customer_code'), 'delivery_history', ['customer_code'], unique=False)
    
    # Create route_plan table
    op.create_table('route_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_date', sa.Date(), nullable=False),
        sa.Column('total_routes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_deliveries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('optimized', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('optimization_params', sa.JSON(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_route_plan_plan_date'), 'route_plan', ['plan_date'], unique=False)
    
    # Create driver_assignments table
    op.create_table('driver_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('route_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('delivery_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['route_plan.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_driver_assignments_plan_id'), 'driver_assignments', ['plan_id'], unique=False)
    op.create_index(op.f('ix_driver_assignments_driver_id'), 'driver_assignments', ['driver_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('driver_assignments')
    op.drop_table('route_plan')
    op.drop_table('delivery_history')
    op.drop_table('delivery_status_history')
    op.drop_table('route_deliveries')
    op.drop_table('prediction_batch')
    op.drop_table('customer_inventory')
    op.drop_table('credit_notes')
    op.drop_table('payments')
    op.drop_table('invoice_items')
    op.drop_table('invoices')
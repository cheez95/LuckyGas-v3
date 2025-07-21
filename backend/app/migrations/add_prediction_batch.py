"""
Add prediction batch table and batch_id to predictions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # Create prediction_batches table
    op.create_table(
        'prediction_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('total_customers', sa.Integer(), nullable=True, default=0),
        sa.Column('processed_customers', sa.Integer(), nullable=True, default=0),
        sa.Column('successful_predictions', sa.Integer(), nullable=True, default=0),
        sa.Column('failed_predictions', sa.Integer(), nullable=True, default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_batches_id'), 'prediction_batches', ['id'], unique=False)
    
    # Add batch_id to delivery_predictions
    op.add_column('delivery_predictions', sa.Column('batch_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_delivery_predictions_batch_id'), 'delivery_predictions', ['batch_id'], unique=False)
    op.create_foreign_key(
        'fk_delivery_predictions_batch_id',
        'delivery_predictions', 'prediction_batches',
        ['batch_id'], ['id']
    )


def downgrade():
    # Remove foreign key and column from delivery_predictions
    op.drop_constraint('fk_delivery_predictions_batch_id', 'delivery_predictions', type_='foreignkey')
    op.drop_index(op.f('ix_delivery_predictions_batch_id'), table_name='delivery_predictions')
    op.drop_column('delivery_predictions', 'batch_id')
    
    # Drop prediction_batches table
    op.drop_index(op.f('ix_prediction_batches_id'), table_name='prediction_batches')
    op.drop_table('prediction_batches')
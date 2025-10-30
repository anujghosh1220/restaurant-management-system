"""Add discount fields to MenuItem

Revision ID: 1234567890ab
Revises: fbd99ac2d90d
Create Date: 2025-03-20 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = 'fbd99ac2d90d'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns
    op.add_column('menu_item', sa.Column('original_price', sa.Float(), nullable=True))
    op.add_column('menu_item', sa.Column('discount_percentage', sa.Float(), server_default='0.0', nullable=True))
    op.add_column('menu_item', sa.Column('discount_start', sa.DateTime(), nullable=True))
    op.add_column('menu_item', sa.Column('discount_end', sa.DateTime(), nullable=True))
    
    # Set original_price to current price for existing items
    op.execute('UPDATE menu_item SET original_price = price')
    
    # Make original_price non-nullable after setting values
    with op.batch_alter_table('menu_item') as batch_op:
        batch_op.alter_column('original_price', nullable=False)

def downgrade():
    with op.batch_alter_table('menu_item') as batch_op:
        batch_op.drop_column('discount_end')
        batch_op.drop_column('discount_start')
        batch_op.drop_column('discount_percentage')
        batch_op.drop_column('original_price')

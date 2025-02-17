"""changes

Revision ID: 18ac2c6fa8f9
Revises: 6d4b0d7d3815
Create Date: 2025-02-14 21:58:44.073067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18ac2c6fa8f9'
down_revision: Union[str, None] = '6d4b0d7d3815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customers', sa.Column('creted_by_customer_id', sa.Integer(), nullable=True))
    op.add_column('tickets', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('tickets', sa.Column('status', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tickets', 'status')
    op.drop_column('tickets', 'tenant_id')
    op.drop_column('customers', 'creted_by_customer_id')
    # ### end Alembic commands ###

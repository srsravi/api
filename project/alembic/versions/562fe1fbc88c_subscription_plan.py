"""Subscription plan

Revision ID: 562fe1fbc88c
Revises: f23f623cd5e8
Create Date: 2024-11-13 19:42:10.024339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '562fe1fbc88c'
down_revision: Union[str, None] = 'f23f623cd5e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('application_details', sa.Column('tenant_id', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('application_details', 'tenant_id')
    # ### end Alembic commands ###

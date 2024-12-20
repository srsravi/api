"""payments

Revision ID: 432afb4ea4f1
Revises: 5942c5b9ab56
Create Date: 2024-12-15 19:37:04.576512

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '432afb4ea4f1'
down_revision: Union[str, None] = '5942c5b9ab56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customers', sa.Column('gender', sa.String(length=150), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('customers', 'gender')
    # ### end Alembic commands ###

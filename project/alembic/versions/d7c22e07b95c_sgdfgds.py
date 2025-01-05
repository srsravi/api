"""sgdfgds

Revision ID: d7c22e07b95c
Revises: 1bd73af48795
Create Date: 2025-01-05 10:54:15.012689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd7c22e07b95c'
down_revision: Union[str, None] = '1bd73af48795'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('customer_details', 'lastYearITRamount',
               existing_type=mysql.INTEGER(display_width=11),
               type_=sa.Float(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('customer_details', 'lastYearITRamount',
               existing_type=sa.Float(),
               type_=mysql.INTEGER(display_width=11),
               existing_nullable=True)
    # ### end Alembic commands ###

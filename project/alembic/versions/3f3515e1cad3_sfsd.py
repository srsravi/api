"""sfsd

Revision ID: 3f3515e1cad3
Revises: 6b83880c34f0
Create Date: 2024-11-24 17:32:17.573225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '3f3515e1cad3'
down_revision: Union[str, None] = '6b83880c34f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    op.alter_column('customers', 'service_type_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('customers', 'service_type_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###
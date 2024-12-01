"""Enquiry

Revision ID: 6b83880c34f0
Revises: 8a213896d956
Create Date: 2024-11-23 21:20:52.096551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '6b83880c34f0'
down_revision: Union[str, None] = '8a213896d956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    op.alter_column('enquiries', 'service_type_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('enquiries', 'service_type_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###
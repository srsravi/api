"""enquiry model added

Revision ID: da573f25c395
Revises: d4d2b44a0e24
Create Date: 2024-11-23 11:17:56.263125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'da573f25c395'
down_revision: Union[str, None] = 'd4d2b44a0e24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    op.add_column('enquiries', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('enquiries', sa.Column('tenant_id', sa.Integer(), autoincrement=True, nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('enquiries', 'tenant_id')
    op.drop_column('enquiries', 'description')
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###

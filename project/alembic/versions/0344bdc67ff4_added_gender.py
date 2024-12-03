"""Added Gender

Revision ID: 0344bdc67ff4
Revises: 79b20eac7a9f
Create Date: 2024-12-02 21:51:57.458791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '0344bdc67ff4'
down_revision: Union[str, None] = '79b20eac7a9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('admin', sa.Column('gender', sa.String(length=15), nullable=True))
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    op.drop_column('admin', 'gender')
    # ### end Alembic commands ###

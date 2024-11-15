"""dhsdj

Revision ID: a4dffd9c6e55
Revises: 2d072c590e7d
Create Date: 2024-11-15 21:25:46.428535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'a4dffd9c6e55'
down_revision: Union[str, None] = '2d072c590e7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('application_details', sa.Column('eligible', sa.String(length=5), nullable=True))
    op.add_column('application_details', sa.Column('loan_eligible_type', sa.Integer(), nullable=True))
    op.add_column('application_details', sa.Column('loan_eligible_amount', sa.Float(), nullable=True))
    op.add_column('application_details', sa.Column('fdir', sa.Text(), nullable=True))
    op.add_column('application_details', sa.Column('description', sa.Text(), nullable=True, comment='description'))
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.FLOAT(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('application_details', 'loanAmount',
               existing_type=mysql.FLOAT(),
               nullable=False)
    op.drop_column('application_details', 'description')
    op.drop_column('application_details', 'fdir')
    op.drop_column('application_details', 'loan_eligible_amount')
    op.drop_column('application_details', 'loan_eligible_type')
    op.drop_column('application_details', 'eligible')
    # ### end Alembic commands ###

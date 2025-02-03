"""tickets

Revision ID: 61ee1ec4a491
Revises: ddc6db8a64e0
Create Date: 2025-02-03 07:24:27.075797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61ee1ec4a491'
down_revision: Union[str, None] = 'ddc6db8a64e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ticket_comments', sa.Column('admin_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_ticket_comments_admin_id'), 'ticket_comments', ['admin_id'], unique=False)
    op.create_foreign_key(None, 'ticket_comments', 'admin', ['admin_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'ticket_comments', type_='foreignkey')
    op.drop_index(op.f('ix_ticket_comments_admin_id'), table_name='ticket_comments')
    op.drop_column('ticket_comments', 'admin_id')
    # ### end Alembic commands ###

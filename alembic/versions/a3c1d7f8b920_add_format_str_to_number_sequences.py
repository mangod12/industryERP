"""add_format_str_to_number_sequences

Revision ID: a3c1d7f8b920
Revises: f9175aa2e862
Create Date: 2026-05-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c1d7f8b920'
down_revision: Union[str, None] = 'f9175aa2e862'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('number_sequences', schema=None) as batch_op:
        batch_op.add_column(sa.Column('format_str', sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('number_sequences', schema=None) as batch_op:
        batch_op.drop_column('format_str')

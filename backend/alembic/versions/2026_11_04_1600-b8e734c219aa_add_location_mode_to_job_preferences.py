"""add_location_mode_to_job_preferences

Revision ID: b8e734c219aa
Revises: 4ad244505177
Create Date: 2026-11-04 16:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8e734c219aa'
down_revision: Union[str, None] = '4ad244505177'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'job_preferences',
        sa.Column('location_mode', sa.String(length=50), server_default='INDIA_ONLY', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('job_preferences', 'location_mode')

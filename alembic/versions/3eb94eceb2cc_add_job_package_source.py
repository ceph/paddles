"""add_job_package_source

Revision ID: 3eb94eceb2cc
Revises: cf54532418e7
Create Date: 2026-07-17 10:52:25.599609

"""

# revision identifiers, used by Alembic.
revision = '3eb94eceb2cc'
down_revision = 'cf54532418e7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'jobs',
        sa.Column('package_source', sa.String(32), nullable=True),
    )


def downgrade():
    op.drop_column('jobs', 'package_source')

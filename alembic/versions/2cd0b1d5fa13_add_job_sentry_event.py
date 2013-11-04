"""Add Job.sentry_event

Revision ID: 2cd0b1d5fa13
Revises: 39c1c8ab81d3
Create Date: 2013-11-04 13:51:44.052755

"""

# revision identifiers, used by Alembic.
revision = '2cd0b1d5fa13'
down_revision = '39c1c8ab81d3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('sentry_event', sa.String(length=128),
                                    nullable=True))


def downgrade():
    op.drop_column('jobs', 'sentry_event')

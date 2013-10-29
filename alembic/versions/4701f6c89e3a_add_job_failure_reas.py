"""Add Job.failure_reason

Revision ID: 4701f6c89e3a
Revises: 40bf4a529955
Create Date: 2013-10-29 11:05:35.100758

"""

# revision identifiers, used by Alembic.
revision = '4701f6c89e3a'
down_revision = '40bf4a529955'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('failure_reason', sa.Text,
                                    nullable=True))


def downgrade():
    op.drop_column('jobs', 'failure_reason')

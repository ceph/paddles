"""Add Job.started and Run.started

Revision ID: 58595304b2a0
Revises: 1bfaa08f247d
Create Date: 2014-04-07 14:48:28.472942

"""

# revision identifiers, used by Alembic.
revision = '58595304b2a0'
down_revision = '1bfaa08f247d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('started', sa.DateTime(), nullable=True))
    op.add_column('runs', sa.Column('started', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('runs', 'started')
    op.drop_column('jobs', 'started')

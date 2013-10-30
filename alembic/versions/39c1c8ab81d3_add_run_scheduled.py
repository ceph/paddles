"""Add run.scheduled

Revision ID: 39c1c8ab81d3
Revises: 4701f6c89e3a
Create Date: 2013-10-30 16:45:47.361357

"""

# revision identifiers, used by Alembic.
revision = '39c1c8ab81d3'
down_revision = '4701f6c89e3a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('runs', sa.Column('scheduled', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('runs', 'scheduled')

"""Add Job.updated

Revision ID: 331ebd570f44
Revises: 41d8ecc1590a
Create Date: 2013-10-23 11:03:46.337153

"""

# revision identifiers, used by Alembic.
revision = '331ebd570f44'
down_revision = '41d8ecc1590a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('updated', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('jobs', 'updated')

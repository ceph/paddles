"""add user fields

Revision ID: 2d1e995efc52
Revises: 2c1851ec5f06
Create Date: 2016-03-01 01:39:11.824364

"""

# revision identifiers, used by Alembic.
revision = '2d1e995efc52'
down_revision = '2c1851ec5f06'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('issue_url', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('comment', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('jobs', 'issue_url')
    op.drop_column('jobs', 'comment')

"""add ceph and ceph-qa-suite fields

Revision ID: 4b86caad387e
Revises: 2d1e995efc52
Create Date: 2016-03-03 16:56:24.681108

"""

# revision identifiers, used by Alembic.
revision = '4b86caad387e'
down_revision = '2d1e995efc52'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('sha1', sa.String(length=40),
                                    nullable=True))
    op.add_column('jobs', sa.Column('branch', sa.String(length=64),
                                    nullable=True))
    op.add_column('jobs', sa.Column('suite_sha1', sa.String(length=40),
                                    nullable=True))

def downgrade():
    op.drop_column('jobs', 'sha1')
    op.drop_column('jobs', 'branch')
    op.drop_column('jobs', 'suite_sha1')

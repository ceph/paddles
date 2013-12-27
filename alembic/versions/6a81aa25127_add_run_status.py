"""Add Run.status

Revision ID: 6a81aa25127
Revises: 3d3dfcb6d22
Create Date: 2013-12-27 09:47:26.875748

"""

# revision identifiers, used by Alembic.
revision = '6a81aa25127'
down_revision = '3d3dfcb6d22'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('runs', sa.Column('status', sa.String(length=16),
                                    nullable=True))
    print "Now, you may want to run the set_status command"


def downgrade():
    op.drop_column('runs', 'status')

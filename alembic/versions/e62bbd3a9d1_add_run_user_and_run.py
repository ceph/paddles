"""Add Run.user and Run.machine_type

Revision ID: e62bbd3a9d1
Revises: 6a81aa25127
Create Date: 2013-12-27 14:11:35.619433

"""

# revision identifiers, used by Alembic.
revision = 'e62bbd3a9d1'
down_revision = '6a81aa25127'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('runs', sa.Column('machine_type', sa.String(length=32),
                                    nullable=True))
    op.add_column('runs', sa.Column('user', sa.String(length=32),
                                    nullable=True))


def downgrade():
    op.drop_column('runs', 'user')
    op.drop_column('runs', 'machine_type')

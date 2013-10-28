"""Add Run.suite

Revision ID: 40bf4a529955
Revises: 10e5bab61d0f
Create Date: 2013-10-29 09:40:54.327823

"""

# revision identifiers, used by Alembic.
revision = '40bf4a529955'
down_revision = '10e5bab61d0f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('runs', sa.Column('suite', sa.String(length=64),
                                    nullable=True))


def downgrade():
    op.drop_column('runs', 'suite')

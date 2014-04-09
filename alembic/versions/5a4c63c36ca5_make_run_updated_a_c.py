"""Make Run.updated a column

Revision ID: 5a4c63c36ca5
Revises: 58595304b2a0
Create Date: 2014-04-09 13:06:17.487246

"""

# revision identifiers, used by Alembic.
revision = '5a4c63c36ca5'
down_revision = '58595304b2a0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('runs', sa.Column('updated', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('runs', 'updated')

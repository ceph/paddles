"""Make Run.name unique

Revision ID: 4bf00b6a85bf
Revises: e62bbd3a9d1
Create Date: 2013-12-27 18:25:27.542487

"""

# revision identifiers, used by Alembic.
revision = '4bf00b6a85bf'
down_revision = 'e62bbd3a9d1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_unique_constraint("uq_run_name", "runs", ["name"])


def downgrade():
    op.drop_constraint("uq_run_name", "runs")

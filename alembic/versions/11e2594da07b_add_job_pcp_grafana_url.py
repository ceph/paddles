"""Add Job.pcp_grafana_url

Revision ID: 11e2594da07b
Revises: 4b86caad387e
Create Date: 2016-05-13 13:33:17.234172

"""

# revision identifiers, used by Alembic.
revision = '11e2594da07b'
down_revision = '4b86caad387e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'jobs',
        sa.Column('pcp_grafana_url', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column('jobs', 'pcp_grafana_url')

"""job_nodes: add composite index on node_id, job_id

Revision ID: a87fde18c8c6
Revises: e8de4928657
Create Date: 2026-05-06 09:49:40.626887

"""

# revision identifiers, used by Alembic.
revision = 'a87fde18c8c6'
down_revision = 'e8de4928657'

from alembic import op


def upgrade():
    op.create_index('ix_job_nodes_node_id_job_id', 'job_nodes', ['node_id', 'job_id'])


def downgrade():
    op.drop_index('ix_job_nodes_node_id_job_id', table_name='job_nodes')

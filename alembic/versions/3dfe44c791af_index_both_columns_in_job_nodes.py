"""Index both columns in job_nodes

Revision ID: 3dfe44c791af
Revises: 3e5e9e6679ae
Create Date: 2014-04-23 15:33:15.006019

"""

# revision identifiers, used by Alembic.
revision = '3dfe44c791af'
down_revision = '3e5e9e6679ae'

from alembic import op


def upgrade():
    op.create_index('ix_job_nodes_job_id', 'job_nodes', ['job_id'],
                    unique=False)
    op.create_index('ix_job_nodes_node_id', 'job_nodes', ['node_id'],
                    unique=False)


def downgrade():
    op.drop_index('ix_job_nodes_node_id', table_name='job_nodes')
    op.drop_index('ix_job_nodes_job_id', table_name='job_nodes')

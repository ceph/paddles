"""Index Node.name

Revision ID: 3e5e9e6679ae
Revises: 1292c15cd656
Create Date: 2014-04-23 14:49:25.974599

"""

# revision identifiers, used by Alembic.
revision = '3e5e9e6679ae'
down_revision = '1292c15cd656'

from alembic import op


def upgrade():
    op.create_index('ix_nodes_name', 'nodes', ['name'], unique=True)


def downgrade():
    op.drop_index('ix_nodes_name', table_name='nodes')

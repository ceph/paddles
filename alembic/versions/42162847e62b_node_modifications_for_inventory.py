"""Node modifications for inventory

Revision ID: 42162847e62b
Revises: 1e4c91edd48e
Create Date: 2014-09-09 14:48:10.163429

"""

# revision identifiers, used by Alembic.
revision = '42162847e62b'
down_revision = '1e4c91edd48e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Node.os_type
    op.alter_column('nodes',
                    'distro',
                    new_column_name='os_type',
                    type_=sa.String(32),
                    existing_type=sa.String(32),
                    existing_nullable=True,
                    )
    op.create_index('ix_nodes_os_type', 'nodes', ['os_type'], unique=False)

    # Node.os_version
    op.add_column('nodes',
                  sa.Column('os_version', sa.String(length=16), nullable=True))
    op.create_index('ix_nodes_os_version',
                    'nodes', ['os_version'], unique=False)


def downgrade():
    # Node.os_type
    op.drop_index('ix_nodes_os_type', table_name='nodes')
    op.alter_column('nodes',
                    'os_type',
                    new_column_name='distro',
                    type_=sa.String(32),
                    existing_type=sa.String(32),
                    existing_nullable=True,
                    )

    # Node.os_version
    op.drop_index('ix_nodes_os_version', table_name='nodes')
    op.drop_column('nodes', 'os_version')

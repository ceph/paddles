"""Add Job.os_version

Revision ID: 536725ae255d
Revises: 42162847e62b
Create Date: 2014-10-23 09:41:31.063224

"""

# revision identifiers, used by Alembic.
revision = '536725ae255d'
down_revision = '42162847e62b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('os_version', sa.String(length=16),
                                    nullable=True))
    op.drop_index('ix_nodes_os_type', table_name='nodes')


def downgrade():
    op.create_index('ix_nodes_os_type', 'nodes', ['os_type'], unique=False)
    op.drop_column('jobs', 'os_version')

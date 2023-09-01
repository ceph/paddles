"""Index Run.name

Revision ID: 266e6f3efd94
Revises: 11e2594da07b
Create Date: 2023-07-31 12:01:24.936988

"""

# revision identifiers, used by Alembic.
revision = '266e6f3efd94'
down_revision = '11e2594da07b'

from alembic import op


def upgrade():
    op.create_index('ix_runs_name', 'runs', ['name'], unique=True)


def downgrade():
    op.drop_index('ix_runs_name', table_name='runs')

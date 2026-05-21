"""jobs: add covering index on id including posted, started, updated

Revision ID: ed4b99e73654
Revises: a472105a9606
Create Date: 2026-05-15 15:23:43.082866

"""

# revision identifiers, used by Alembic.
revision = 'ed4b99e73654'
down_revision = 'a472105a9606'

from alembic import op

def upgrade():
    with op.get_context().autocommit_block():
        op.create_index(
            'ix_jobs_id_covering',
            'jobs',
            ['id'],
            postgresql_include=['posted', 'started', 'updated'],
            postgresql_concurrently=True,
        )

def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index(
            'ix_jobs_id_covering',
            table_name='jobs',
            postgresql_concurrently=True,
        )

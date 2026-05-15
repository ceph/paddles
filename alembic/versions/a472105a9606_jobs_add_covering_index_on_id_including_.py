"""jobs: add covering index on id including posted for node lookup sorting

Revision ID: a472105a9606
Revises: 5d51c1a96ecc
Create Date: 2026-05-15 11:26:16.247010

"""

# revision identifiers, used by Alembic.
revision = 'a472105a9606'
down_revision = '5d51c1a96ecc'

from alembic import op

def upgrade():
    with op.get_context().autocommit_block():
        op.create_index(
            'ix_jobs_id_posted',
            'jobs',
            ['id'],
            postgresql_include=['posted'],
            postgresql_concurrently=True,
        )

def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index(
            'ix_jobs_id_posted',
            table_name='jobs',
            postgresql_concurrently=True,
        )

"""jobs: add text_pattern_ops index on sha1 for LIKE prefix search

Revision ID: cf54532418e7
Revises: ed4b99e73654
Create Date: 2026-05-19 12:24:21.143316

"""

# revision identifiers, used by Alembic.
revision = 'cf54532418e7'
down_revision = 'ed4b99e73654'

from alembic import op
import sqlalchemy as sa

def upgrade():
    with op.get_context().autocommit_block():
        op.create_index(
            'ix_jobs_sha1_pattern',
            'jobs',
            ['sha1'],
            postgresql_ops={'sha1': 'text_pattern_ops'},
            postgresql_concurrently=True,
        )

def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index(
            'ix_jobs_sha1_pattern',
            table_name='jobs',
            postgresql_concurrently=True,
        )

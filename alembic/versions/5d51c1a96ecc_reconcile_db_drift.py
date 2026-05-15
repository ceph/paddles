"""reconcile db drift

Revision ID: 5d51c1a96ecc
Revises: a87fde18c8c6
Create Date: 2026-05-15 11:07:43.754294

"""

# revision identifiers, used by Alembic.
revision = '5d51c1a96ecc'
down_revision = 'a87fde18c8c6'

from alembic import op


def upgrade():
    with op.get_context().autocommit_block():
        # Replace legacy oddly-named indexes with proper alembic-named ones
        op.drop_index('jobs_idx', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('jobs_success_idx', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('runs_timestamp_idx', table_name='runs',
                      postgresql_concurrently=True)

        # jobs indexes
        op.create_index('ix_jobs_posted', 'jobs', ['posted'],
                        postgresql_concurrently=True)
        op.create_index('ix_jobs_success', 'jobs', ['success'],
                        postgresql_concurrently=True)
        op.create_index('ix_jobs_branch', 'jobs', ['branch'],
                        postgresql_concurrently=True)
        op.create_index('ix_jobs_priority', 'jobs', ['priority'],
                        postgresql_concurrently=True)
        op.create_index('ix_jobs_queue', 'jobs', ['queue'],
                        postgresql_concurrently=True)
        op.create_index('ix_jobs_suite_sha1', 'jobs', ['suite_sha1'],
                        postgresql_concurrently=True)
        op.create_index('ix_jobs_updated', 'jobs', ['updated'],
                        postgresql_concurrently=True)

        # runs indexes
        op.create_index('ix_runs_branch', 'runs', ['branch'],
                        postgresql_concurrently=True)
        op.create_index('ix_runs_posted', 'runs', ['posted'],
                        postgresql_concurrently=True)
        op.create_index('ix_runs_suite', 'runs', ['suite'],
                        postgresql_concurrently=True)


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index('ix_runs_suite', table_name='runs',
                      postgresql_concurrently=True)
        op.drop_index('ix_runs_posted', table_name='runs',
                      postgresql_concurrently=True)
        op.drop_index('ix_runs_branch', table_name='runs',
                      postgresql_concurrently=True)
        op.drop_index('ix_jobs_updated', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('ix_jobs_suite_sha1', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('ix_jobs_queue', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('ix_jobs_priority', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('ix_jobs_branch', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('ix_jobs_success', table_name='jobs',
                      postgresql_concurrently=True)
        op.drop_index('ix_jobs_posted', table_name='jobs',
                      postgresql_concurrently=True)
        op.create_index('runs_timestamp_idx', 'runs', ['posted'],
                        postgresql_concurrently=True)
        op.create_index('jobs_success_idx', 'jobs', ['success'],
                        postgresql_concurrently=True)
        op.create_index('jobs_idx', 'jobs', ['posted'],
                        postgresql_concurrently=True)

"""modify jobs table

Revision ID: e8de4928657
Revises: 266e6f3efd94
Create Date: 2021-06-28 13:45:32.717585

"""

# revision identifiers, used by Alembic.
revision = 'e8de4928657'
down_revision = '266e6f3efd94'

from alembic import op
from paddles.models.types import JSONType
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence

import sqlalchemy as sa


def upgrade():
    op.add_column(u'jobs', sa.Column('priority', sa.Integer(), nullable=True))
    op.add_column(u'jobs', sa.Column('repo', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('seed', sa.Integer(), nullable=True))
    op.add_column(u'jobs', sa.Column('sleep_before_teardown', sa.Integer(), nullable=True))
    op.add_column(u'jobs', sa.Column('subset', sa.String(length=32), nullable=True))
    op.add_column(u'jobs', sa.Column('suite', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('suite_path', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('suite_relpath', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('suite_repo', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('teuthology_branch', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('teuthology_sha1', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('timestamp', sa.DateTime(), nullable=True))
    op.add_column(u'jobs', sa.Column('user', sa.String(length=64), nullable=True))
    op.add_column(u'jobs', sa.Column('queue', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_jobs_job_id'), 'jobs', ['job_id'], unique=False)
    op.create_index(op.f('ix_jobs_teuthology_sha1'), 'jobs', ['teuthology_sha1'], unique=False)
    op.execute(CreateSequence(Sequence('jobs_id_seq')))
    op.drop_index('ix_jobs_archive_path', table_name='jobs')


def downgrade():
    op.create_index('ix_jobs_archive_path', 'jobs', ['archive_path'], unique=False)
    op.drop_index(op.f('ix_jobs_teuthology_sha1'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_job_id'), table_name='jobs')
    op.execute(DropSequence(Sequence('jobs_id_seq')))
    op.drop_column(u'jobs', 'user')
    op.drop_column(u'jobs', 'timestamp')
    op.drop_column(u'jobs', 'teuthology_sha1')
    op.drop_column(u'jobs', 'suite_repo')
    op.drop_column(u'jobs', 'suite_relpath')
    op.drop_column(u'jobs', 'suite')
    op.drop_column(u'jobs', 'sleep_before_teardown')
    op.drop_column(u'jobs', 'repo')
    op.drop_column(u'jobs', 'priority')


"""modify jobs table

Revision ID: e8de4928657
Revises: 11e2594da07b
Create Date: 2021-06-28 13:45:32.717585

"""

# revision identifiers, used by Alembic.
revision = 'e8de4928657'
down_revision = '11e2594da07b'

from alembic import op
from paddles.models.types import JSONType
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence

import sqlalchemy as sa


def upgrade():
    op.add_column(u'jobs', sa.Column('first_in_suite', sa.Boolean(), nullable=True))
    op.add_column(u'jobs', sa.Column('openstack', JSONType(), nullable=True))
    op.add_column(u'jobs', sa.Column('priority', sa.Integer(), nullable=True))
    op.add_column(u'jobs', sa.Column('repo', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('sleep_before_teardown', sa.Integer(), nullable=True))
    op.add_column(u'jobs', sa.Column('suite', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('suite_relpath', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('suite_repo', sa.String(length=256), nullable=True))
    op.add_column(u'jobs', sa.Column('teuthology_sha1', sa.String(length=40), nullable=True))
    op.add_column(u'jobs', sa.Column('timestamp', sa.DateTime(), nullable=True))
    op.add_column(u'jobs', sa.Column('user', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_jobs_job_id'), 'jobs', ['job_id'], unique=False)
    op.create_index(op.f('ix_jobs_teuthology_sha1'), 'jobs', ['teuthology_sha1'], unique=False)
    op.execute(CreateSequence(Sequence('job_id_sequence')))
    op.drop_index('ix_jobs_archive_path', table_name='jobs')


def downgrade():
    op.create_index('ix_jobs_archive_path', 'jobs', ['archive_path'], unique=False)
    op.drop_index(op.f('ix_jobs_teuthology_sha1'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_job_id'), table_name='jobs')
    op.execute(DropSequence(Sequence('job_id_sequence')))
    op.drop_column(u'jobs', 'user')
    op.drop_column(u'jobs', 'timestamp')
    op.drop_column(u'jobs', 'teuthology_sha1')
    op.drop_column(u'jobs', 'suite_repo')
    op.drop_column(u'jobs', 'suite_relpath')
    op.drop_column(u'jobs', 'suite')
    op.drop_column(u'jobs', 'sleep_before_teardown')
    op.drop_column(u'jobs', 'repo')
    op.drop_column(u'jobs', 'priority')
    op.drop_column(u'jobs', 'openstack')
    op.drop_column(u'jobs', 'first_in_suite')


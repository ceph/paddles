"""Add Job.suite_branch

Revision ID: 1e4c91edd48e
Revises: 3dfe44c791af
Create Date: 2014-08-07 08:42:43.339794

"""

# revision identifiers, used by Alembic.
revision = '1e4c91edd48e'
down_revision = '3dfe44c791af'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('suite_branch',
                                    sa.String(length=64),
                                    nullable=True))
    op.create_index('ix_jobs_suite_branch',
                    'jobs',
                    ['suite_branch'],
                    unique=False)


def downgrade():
    op.drop_index('ix_jobs_suite_branch', table_name='jobs')
    op.drop_column('jobs', 'suite_branch')

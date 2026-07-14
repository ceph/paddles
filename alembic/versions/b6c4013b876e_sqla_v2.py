"""sqla v2

Revision ID: b6c4013b876e
Revises: cf54532418e7
Create Date: 2026-06-02 00:03:56.532260

"""

# revision identifiers, used by Alembic.
revision = 'b6c4013b876e'
down_revision = 'cf54532418e7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Node.up is not nullable
    op.alter_column('nodes', 'up',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    # Node.machine_type is not nullable
    op.alter_column('nodes', 'machine_type',
               existing_type=sa.VARCHAR(length=32),
               nullable=False)
    # Job.job_id is not nullable
    op.alter_column('jobs', 'job_id',
               existing_type=sa.VARCHAR(length=32),
               nullable=False)
    # run_id/job_id pairs must be unique
    op.create_unique_constraint(None, 'jobs', ['run_id', 'job_id'])


def downgrade():
    op.alter_column('nodes', 'machine_type',
               existing_type=sa.VARCHAR(length=32),
               nullable=True)
    op.alter_column('nodes', 'up',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.drop_constraint(None, 'jobs', type_='unique')
    op.alter_column('jobs', 'job_id',
               existing_type=sa.VARCHAR(length=32),
               nullable=True)

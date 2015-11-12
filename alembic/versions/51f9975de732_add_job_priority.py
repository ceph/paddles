"""Add Job.priority

Revision ID: 51f9975de732
Revises: 536725ae255d
Create Date: 2015-11-12 13:19:25.105482

"""

# revision identifiers, used by Alembic.
revision = '51f9975de732'
down_revision = '536725ae255d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobs', sa.Column('priority', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_jobs_priority'), 'jobs', ['priority'],
                    unique=False)


def downgrade():
    op.drop_index(op.f('ix_jobs_priority'), table_name='jobs')
    op.drop_column('jobs', 'priority')

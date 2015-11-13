"""Change Job.job_id to Integer

Revision ID: 35aada4e1f89
Revises: 51f9975de732
Create Date: 2015-11-12 14:58:05.907759

"""

# revision identifiers, used by Alembic.
revision = '35aada4e1f89'
down_revision = '51f9975de732'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN job_id TYPE integer USING (job_id::integer);"  # noqa
    )


def downgrade():
    op.alter_column('jobs',
                    'job_id',
                    type_=sa.String(32),
                    existing_type=sa.Integer,
                    existing_nullable=False,
                    )

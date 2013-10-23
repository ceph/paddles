"""Rename Run.timestamp and Job.timestamp to 'posted'

Revision ID: 10e5bab61d0f
Revises: 331ebd570f44
Create Date: 2013-10-23 12:27:10.572618

"""

# revision identifiers, used by Alembic.
revision = '10e5bab61d0f'
down_revision = '331ebd570f44'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('jobs',
                    'timestamp',
                    new_column_name='posted',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(),
                    existing_nullable=True,
                    )
    op.alter_column('runs',
                    'timestamp',
                    new_column_name='posted',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(),
                    existing_nullable=True,
                    )


def downgrade():
    op.alter_column('jobs',
                    'posted',
                    new_column_name='timestamp',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(),
                    existing_nullable=True,
                    )
    op.alter_column('runs',
                    'posted',
                    new_column_name='timestamp',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(),
                    existing_nullable=True,
                    )

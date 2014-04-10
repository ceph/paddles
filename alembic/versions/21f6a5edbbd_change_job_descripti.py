"""Change Job.description to type Text

Revision ID: 21f6a5edbbd
Revises: 5a4c63c36ca5
Create Date: 2014-04-10 10:10:13.798682

"""

# revision identifiers, used by Alembic.
revision = '21f6a5edbbd'
down_revision = '5a4c63c36ca5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('jobs',
                    'description',
                    type_=sa.Text(),
                    existing_type=sa.String(512),
                    existing_nullable=True,
                    )


def downgrade():
    op.alter_column('jobs',
                    'description',
                    type_=sa.String(512),
                    existing_type=sa.Text(),
                    existing_nullable=True,
                    )

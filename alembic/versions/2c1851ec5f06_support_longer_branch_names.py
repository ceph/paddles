"""Support longer branch names.

Revision ID: 2c1851ec5f06
Revises: 536725ae255d
Create Date: 2015-12-11 21:30:23.831711

"""

# revision identifiers, used by Alembic.
revision = '2c1851ec5f06'
down_revision = '536725ae255d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('runs',
                    'suite',
                    type_=sa.String(256),
                    existing_type=sa.String(64),
                    )
    op.alter_column('runs',
                    'branch',
                    type_=sa.String(128),
                    existing_type=sa.String(64),
                    )



def downgrade():
    op.alter_column('runs',
                    'suite',
                    type_=sa.String(64),
                    existing_type=sa.String(256),
                    )
    op.alter_column('runs',
                    'branch',
                    type_=sa.String(64),
                    existing_type=sa.String(128),
                    )

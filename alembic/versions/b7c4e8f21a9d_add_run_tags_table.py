"""add_run_tags_table

Revision ID: b7c4e8f21a9d
Revises: 3eb94eceb2cc
Create Date: 2026-11-12 00:00:00.000000

"""

revision = 'b7c4e8f21a9d'
down_revision = '3eb94eceb2cc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'run_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(
            ['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'tag', name='uq_run_tags_run_id_tag'),
    )
    op.create_index(
        op.f('ix_run_tags_run_id'), 'run_tags', ['run_id'], unique=False)
    op.create_index(
        op.f('ix_run_tags_tag'), 'run_tags', ['tag'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_run_tags_tag'), table_name='run_tags')
    op.drop_index(op.f('ix_run_tags_run_id'), table_name='run_tags')
    op.drop_table('run_tags')

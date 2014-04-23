"""Add several indexes

Revision ID: 1292c15cd656
Revises: 21f6a5edbbd
Create Date: 2014-04-22 18:19:46.727586

"""

# revision identifiers, used by Alembic.
revision = '1292c15cd656'
down_revision = '21f6a5edbbd'

from alembic import op


def upgrade():
    op.create_index('ix_jobs_run_id', 'jobs', ['run_id'], unique=False)
    op.create_index('ix_jobs_started', 'jobs', ['started'], unique=False)
    op.create_index('ix_jobs_status', 'jobs', ['status'], unique=False)
    op.create_index('ix_nodes_locked', 'nodes', ['locked'], unique=False)
    op.create_index('ix_nodes_locked_by', 'nodes', ['locked_by'], unique=False)
    op.create_index('ix_nodes_machine_type', 'nodes', ['machine_type'],
                    unique=False)
    op.create_index('ix_nodes_up', 'nodes', ['up'], unique=False)
    op.create_index('ix_runs_machine_type', 'runs', ['machine_type'],
                    unique=False)
    op.create_index('ix_runs_scheduled', 'runs', ['scheduled'], unique=False)
    op.create_index('ix_runs_started', 'runs', ['started'], unique=False)
    op.create_index('ix_runs_status', 'runs', ['status'], unique=False)
    op.create_index('ix_runs_updated', 'runs', ['updated'], unique=False)
    op.create_index('ix_runs_user', 'runs', ['user'], unique=False)


def downgrade():
    op.drop_index('ix_runs_user', table_name='runs')
    op.drop_index('ix_runs_updated', table_name='runs')
    op.drop_index('ix_runs_status', table_name='runs')
    op.drop_index('ix_runs_started', table_name='runs')
    op.drop_index('ix_runs_scheduled', table_name='runs')
    op.drop_index('ix_runs_machine_type', table_name='runs')
    op.drop_index('ix_nodes_up', table_name='nodes')
    op.drop_index('ix_nodes_machine_type', table_name='nodes')
    op.drop_index('ix_nodes_locked_by', table_name='nodes')
    op.drop_index('ix_nodes_locked', table_name='nodes')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_started', table_name='jobs')
    op.drop_index('ix_jobs_run_id', table_name='jobs')

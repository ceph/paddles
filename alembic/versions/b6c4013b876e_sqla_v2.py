"""sqla v2

Revision ID: b6c4013b876e
Revises: 3eb94eceb2cc
Create Date: 2026-06-02 00:03:56.532260

Tightens the schema to match what the SQLAlchemy 2 models declare:
``nodes.up``, ``nodes.machine_type`` and ``jobs.job_id`` become NOT NULL and
``(jobs.run_id, jobs.job_id)`` becomes unique.

Production data (checked against a copy of the Sepia database on
2026-09-02) violates every one of those, so the constraints are preceded by
a cleanup step:

* 3 nodes with ``up IS NULL`` -> ``up = false``
* 40 legacy nodes (2015-era clara/pluto/incerta/rhoda/test hosts) with
  ``machine_type IS NULL`` -> ``machine_type = 'unknown'``
* 78 job rows with ``job_id IS NULL``. They carry no other data (no name,
  description, archive path, targets or tasks) and cannot be addressed
  through the API, so they are deleted.
* 112 ``(run_id, job_id)`` pairs present twice (2015-2021 ``dead``/``pass``
  twins from re-reported jobs). The older row of each pair is deleted.

The ALTER TABLE statements take an ACCESS EXCLUSIVE lock on ``jobs`` for the
duration of a full-table scan (~13 s for 8.5M rows on Sepia's hardware).
Deploy this migration deliberately, not through an unattended image
rollout, and make sure no long-running queries are in flight.
"""

# revision identifiers, used by Alembic.
revision = 'b6c4013b876e'
down_revision = '3eb94eceb2cc'

from alembic import op
import sqlalchemy as sa

UNIQUE_NAME = 'uq_jobs_run_id_job_id'


def _constraint_exists(name):
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return False
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
            {"name": name},
        ).scalar()
    )


def upgrade():
    # --- data cleanup, so the constraints below can be applied ---
    op.execute("UPDATE nodes SET up = false WHERE up IS NULL")
    op.execute("UPDATE nodes SET machine_type = 'unknown' WHERE machine_type IS NULL")
    op.execute(
        "DELETE FROM job_nodes WHERE job_id IN (SELECT id FROM jobs WHERE job_id IS NULL)"
    )
    op.execute("DELETE FROM jobs WHERE job_id IS NULL")
    # Duplicate (run_id, job_id) pairs: keep the newest row of each pair
    op.execute(
        "DELETE FROM job_nodes WHERE job_id IN ("
        " SELECT j.id FROM jobs j WHERE EXISTS ("
        "  SELECT 1 FROM jobs k"
        "  WHERE k.run_id = j.run_id AND k.job_id = j.job_id AND k.id > j.id))"
    )
    op.execute(
        "DELETE FROM jobs j WHERE EXISTS ("
        " SELECT 1 FROM jobs k"
        " WHERE k.run_id = j.run_id AND k.job_id = j.job_id AND k.id > j.id)"
    )

    # --- constraints ---
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
    if not _constraint_exists(UNIQUE_NAME):
        op.create_unique_constraint(UNIQUE_NAME, 'jobs', ['run_id', 'job_id'])


def downgrade():
    if _constraint_exists(UNIQUE_NAME):
        op.drop_constraint(UNIQUE_NAME, 'jobs', type_='unique')
    op.alter_column('jobs', 'job_id',
               existing_type=sa.VARCHAR(length=32),
               nullable=True)
    op.alter_column('nodes', 'machine_type',
               existing_type=sa.VARCHAR(length=32),
               nullable=True)
    op.alter_column('nodes', 'up',
               existing_type=sa.BOOLEAN(),
               nullable=True)

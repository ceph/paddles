"""Add Nodes

Revision ID: 1bfaa08f247d
Revises: 4bf00b6a85bf
Create Date: 2014-03-20 13:37:18.942551

"""

# revision identifiers, used by Alembic.
revision = '1bfaa08f247d'
down_revision = '4bf00b6a85bf'

from alembic import op
import sqlalchemy as sa

machine_type_enum = sa.Enum('plana', 'mira', 'vps', 'burnupi', 'tala', 'saya',
                            'dubia', name='machine_type')


def upgrade():
    op.create_table(
        'nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('up', sa.Boolean(), nullable=True),
        sa.Column('machine_type', sa.String(length=32), nullable=True),
        sa.Column('arch', sa.String(length=16), nullable=True),
        sa.Column('is_vm', sa.Boolean(), nullable=False),
        sa.Column('distro', sa.String(length=32), nullable=True),
        sa.Column('vm_host_id', sa.Integer(), nullable=True),
        sa.Column('locked', sa.Boolean(), nullable=False),
        sa.Column('locked_by', sa.String(length=64), nullable=True),
        sa.Column('locked_since', sa.DateTime(), nullable=True),
        sa.Column('mac_address', sa.String(length=17), nullable=True),
        sa.Column('ssh_pub_key', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['vm_host_id'], ['nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint("uq_node_name", "nodes", ["name"])
    op.create_table(
        'job_nodes',
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
        sa.PrimaryKeyConstraint()
    )


def downgrade():
    op.drop_table('job_nodes')
    op.drop_constraint("uq_node_name", "nodes")
    op.drop_table('nodes')

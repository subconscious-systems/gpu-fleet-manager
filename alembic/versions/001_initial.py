"""initial

Revision ID: 001
Create Date: 2024-02-05 18:06:09.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create GPUs table
    op.create_table(
        'gpus',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_id', sa.String(length=255)),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_memory', sa.Integer(), nullable=False),
        sa.Column('available_memory', sa.Integer(), nullable=False),
        sa.Column('current_jobs', postgresql.ARRAY(postgresql.UUID()), default=[]),
        sa.Column('capabilities', postgresql.JSON(), nullable=False),
        sa.Column('cost_per_hour', sa.Float()),
        sa.Column('last_active', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('spot_request_id', sa.String(length=255)),
        sa.Column('termination_time', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id')
    )

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=50),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('gpu_assigned', sa.String(length=255)),
        sa.Column('error_message', sa.Text),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('max_retries', sa.Integer(), default=3),
        sa.Column('timeout_seconds', sa.Integer()),
        sa.Column('parameters', postgresql.JSON(), nullable=False),
        sa.Column('result_url', sa.String()),
        sa.Column('cost_estimate', sa.Float()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_jobs_status', 'jobs', ['status'])
    op.create_index('idx_jobs_priority', 'jobs', ['priority'])
    op.create_index('idx_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('idx_gpus_status', 'gpus', ['status'])
    op.create_index('idx_gpus_provider', 'gpus', ['provider'])

def downgrade():
    op.drop_table('jobs')
    op.drop_table('gpus')
    op.drop_table('users')

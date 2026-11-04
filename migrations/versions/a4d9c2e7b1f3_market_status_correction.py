"""Market status corrections: a curator's audited data status for a stored observation.

A vendor can fill a trading day with the previous value. The delivery and its build stay unchanged; the decision is
recorded next to the observation and wins in quality, summary and export. Existing rows are untouched.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a4d9c2e7b1f3'
down_revision = '8c3f2a6e1d07'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('market_status_correction',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('observation_id', sa.String(), nullable=False),
    sa.Column('data_status', sa.String(length=16), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('reviewer', sa.String(), nullable=False),
    sa.Column('decided_at', sa.String(), nullable=False),
    sa.CheckConstraint("data_status IN ('reported','provisional','final','carried_forward','corrected')", name='ck_market_correction_status'),
    sa.ForeignKeyConstraint(['observation_id'], ['market_observation.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_status_correction_observation_id', 'market_status_correction', ['observation_id'], unique=False)

def downgrade():
    op.drop_index('ix_market_status_correction_observation_id', table_name='market_status_correction')
    op.drop_table('market_status_correction')

"""Market data area: instruments, observations and their builds; export permission on access decisions.

Added after DC1 (approved 2026-10-26). Market observations keep each instrument, price type and
field separate, in the source's own currency and unit, and cite the registered document version
they were read from. source_access.export_allowed records whether data from a source may leave
the Core in an export; existing decisions keep today's behaviour (allowed).
"""
from alembic import op
import sqlalchemy as sa

revision = '5b1e0c7d9a42'
down_revision = '34e9de7241cf'
branch_labels = None
depends_on = None

PRICE_FIELDS = ('bid', 'ask', 'open', 'high', 'low', 'close', 'settlement')
QUANTITY_FIELDS = ('volume', 'open_interest')

def amount():
    """Exact decimals, as the baseline declares them: NUMERIC(30, 6), text on SQLite."""
    return sa.Numeric(precision=30, scale=6).with_variant(sa.String(40), 'sqlite')

def upgrade():
    with op.batch_alter_table('source_access') as batch:
        batch.add_column(sa.Column('export_allowed', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_table('market_instrument',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('exchange', sa.String(length=16), nullable=True),
    sa.Column('market', sa.String(length=16), nullable=False),
    sa.Column('commodity', sa.String(), nullable=False),
    sa.Column('grade', sa.String(length=256), nullable=True),
    sa.Column('region', sa.String(length=128), nullable=True),
    sa.Column('tenor', sa.String(length=32), nullable=True),
    sa.Column('contract_code', sa.String(length=32), nullable=True),
    sa.Column('contract_month', sa.String(length=7), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('unit', sa.String(length=16), nullable=False),
    sa.Column('quantity_unit', sa.String(length=16), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.String(), nullable=False),
    sa.CheckConstraint("market IN ('forward','futures','physical')", name='ck_instrument_market'),
    sa.CheckConstraint("market = 'physical' OR exchange IS NOT NULL", name='ck_instrument_exchange'),
    sa.CheckConstraint("market <> 'forward' OR tenor IS NOT NULL", name='ck_instrument_forward_tenor'),
    sa.CheckConstraint('tenor IS NULL OR contract_month IS NULL', name='ck_instrument_point_or_contract'),
    sa.CheckConstraint('(contract_code IS NULL) = (contract_month IS NULL)', name='ck_instrument_contract'),
    sa.CheckConstraint("unit IN ('USD/t','USc/lb','USD/lb','CNY/t','EUR/t','JPY/t')", name='ck_instrument_unit'),
    sa.CheckConstraint("quantity_unit IS NULL OR quantity_unit IN ('lots','contracts','t')", name='ck_instrument_quantity_unit'),
    sa.ForeignKeyConstraint(['commodity'], ['commodity.code'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('market_build',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('document_id', sa.String(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('parser_version', sa.String(), nullable=False),
    sa.Column('pipeline_version', sa.String(), nullable=False),
    sa.Column('specification', sa.JSON(), nullable=False),
    sa.Column('logical_output', sa.JSON(), nullable=False),
    sa.Column('output_hash', sa.String(length=64), nullable=False),
    sa.Column('actor', sa.String(), nullable=False),
    sa.Column('created_at', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_build_document_id', 'market_build', ['document_id'], unique=False)
    cast = lambda name: f'CAST({name} AS NUMERIC)'
    op.create_table('market_observation',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('instrument_id', sa.String(), nullable=False),
    sa.Column('document_id', sa.String(), nullable=False),
    sa.Column('build_id', sa.String(length=64), nullable=False),
    sa.Column('price_type', sa.String(length=16), nullable=False),
    sa.Column('effective_date', sa.Date(), nullable=False),
    sa.Column('effective_at', sa.String(length=32), nullable=True),
    sa.Column('contract_code', sa.String(length=32), nullable=True),
    sa.Column('contract_month', sa.String(length=7), nullable=True),
    sa.Column('prompt_date', sa.Date(), nullable=True),
    *[sa.Column(name, amount(), nullable=True) for name in (*PRICE_FIELDS, *QUANTITY_FIELDS)],
    sa.Column('published_at', sa.String(length=32), nullable=True),
    sa.Column('retrieved_at', sa.String(length=32), nullable=False),
    sa.Column('data_status', sa.String(length=16), nullable=False),
    sa.Column('source_series', sa.JSON(), nullable=False),
    sa.Column('evidence_reference', sa.Text(), nullable=False),
    sa.Column('recorded_at', sa.String(), nullable=False),
    sa.CheckConstraint("price_type IN ('official','closing','settlement','daily','assessment','intraday')", name='ck_market_price_type'),
    sa.CheckConstraint("data_status IN ('reported','provisional','final','carried_forward','corrected')", name='ck_market_data_status'),
    sa.CheckConstraint(' OR '.join(f'{name} IS NOT NULL' for name in (*PRICE_FIELDS, *QUANTITY_FIELDS)), name='ck_market_has_value'),
    sa.CheckConstraint(f"high IS NULL OR low IS NULL OR {cast('high')} >= {cast('low')}", name='ck_market_high_low'),
    sa.CheckConstraint(f"bid IS NULL OR ask IS NULL OR {cast('bid')} <= {cast('ask')}", name='ck_market_bid_ask'),
    sa.CheckConstraint(f"volume IS NULL OR {cast('volume')} >= 0", name='ck_market_volume'),
    sa.CheckConstraint(f"open_interest IS NULL OR {cast('open_interest')} >= 0", name='ck_market_open_interest'),
    sa.ForeignKeyConstraint(['build_id'], ['market_build.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.ForeignKeyConstraint(['instrument_id'], ['market_instrument.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_observation_build_id', 'market_observation', ['build_id'], unique=False)
    op.create_index('ix_market_observation_document_id', 'market_observation', ['document_id'], unique=False)
    op.create_index('ix_market_observation_instrument_id', 'market_observation', ['instrument_id'], unique=False)

def downgrade():
    op.drop_index('ix_market_observation_instrument_id', table_name='market_observation')
    op.drop_index('ix_market_observation_document_id', table_name='market_observation')
    op.drop_index('ix_market_observation_build_id', table_name='market_observation')
    op.drop_table('market_observation')
    op.drop_index('ix_market_build_document_id', table_name='market_build')
    op.drop_table('market_build')
    op.drop_table('market_instrument')
    with op.batch_alter_table('source_access') as batch:
        batch.drop_column('export_allowed')

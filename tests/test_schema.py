"""DC1 step A2: one straight migration line; its DC1 baseline creates exactly the 26 Core tables and 3 views.

Later migrations add the market data area (approved 2026-10-26): three tables and source_access.export_allowed.
"""
import json
import re
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from app.models import Base

CORE_TABLES = {'entities', 'company', 'facility', 'country', 'region', 'facility_type', 'commodity', 'entity_alias',
               'entity_supersession', 'entity_evidence', 'sources', 'source_access', 'documents', 'document_version',
               'source_snapshot', 'source_document_relation', 'runs', 'retrieval_attempt', 'observations',
               'observation_detail', 'relationships', 'company_facility_relationship', 'evidence_build', 'candidate',
               'reviews', 'audit'}
MARKET_TABLES = {'market_instrument', 'market_build', 'market_observation'}
VIEWS = {'capacity_observation', 'status_observation', 'facility_alias'}
BASELINE = '34e9de7241cf'
# Today's databases (platform revision d8317b920a11, 2026-10-13), Core tables only.
TODAY = Path(__file__).parent / 'fixtures' / 'schema'

def describe(engine):
    """Normalized structure of the Core tables: columns in order, keys, indexes and checks."""
    inspector = inspect(engine)
    norm = lambda sql: re.sub(r'\s+', ' ', sql or '').strip()
    tables = {}
    for table in sorted(CORE_TABLES):
        tables[table] = {
            'columns': [[c['name'], str(c['type']), c['nullable'], norm(str(c['default'])) if c.get('default') is not None else None] for c in inspector.get_columns(table)],
            'primary_key': sorted(inspector.get_pk_constraint(table)['constrained_columns']),
            'foreign_keys': sorted([fk['constrained_columns'], fk['referred_table'], fk['referred_columns']] for fk in inspector.get_foreign_keys(table)),
            'unique': sorted(sorted(u['column_names']) for u in inspector.get_unique_constraints(table)),
            'indexes': sorted([i['name'], i['column_names'], bool(i['unique'])] for i in inspector.get_indexes(table)),
            'checks': sorted([c.get('name'), norm(c['sqltext'])] for c in inspector.get_check_constraints(table))}
    views = {view: [c['name'] for c in inspector.get_columns(view)] for view in sorted(inspector.get_view_names())}
    return {'tables': tables, 'views': views}

def migrated(new_database, monkeypatch, target='head'):
    url = new_database('schema')
    monkeypatch.setenv('DATABASE_URL', url)
    command.upgrade(Config('alembic.ini'), target)
    return url

def test_single_straight_migration_line():
    script = ScriptDirectory.from_config(Config('alembic.ini'))
    revisions = list(script.walk_revisions())
    assert len(script.get_bases()) == 1 and len(script.get_heads()) == 1
    assert not any(isinstance(revision.down_revision, (tuple, list)) for revision in revisions), 'joined branches'
    assert not any(revision.branch_labels for revision in revisions)

def test_models_declare_exactly_the_core_tables():
    assert set(Base.metadata.tables) == CORE_TABLES | MARKET_TABLES and len(CORE_TABLES) == 26

def test_exact_tables_views_reference_rows_and_drift(new_database, monkeypatch):
    url = migrated(new_database, monkeypatch)
    config = Config('alembic.ini')
    command.check(config)
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == CORE_TABLES | MARKET_TABLES | {'alembic_version'}
        assert set(inspector.get_view_names()) == VIEWS
        with engine.connect() as connection:
            counts = {table: connection.execute(text(f'SELECT count(*) FROM {table}')).scalar() for table in ('country', 'commodity', 'facility_type')}
        assert counts == {'country': 30, 'commodity': 3, 'facility_type': 3}  # 28 in the DC1 baseline, then Austria and Japan
        command.downgrade(config, 'base')
        assert set(inspect(engine).get_table_names()) <= {'alembic_version'} and not inspect(engine).get_view_names()
        command.upgrade(config, BASELINE)
        assert set(inspect(engine).get_table_names()) == CORE_TABLES | {'alembic_version'}
        command.upgrade(config, 'head')
        assert set(inspect(engine).get_table_names()) == CORE_TABLES | MARKET_TABLES | {'alembic_version'}
    finally:
        engine.dispose()

def test_baseline_matches_todays_core_tables(new_database, monkeypatch):
    url = migrated(new_database, monkeypatch, BASELINE)
    engine = create_engine(url)
    try: actual = describe(engine)
    finally: engine.dispose()
    expected = json.loads((TODAY / f'today-{engine.dialect.name}.json').read_text())
    # Deliberate differences, documented in the baseline migration:
    # - the platform's source_access.usage_scope is not a Core column: every Core source is evidence;
    # - PostgreSQL databases carry two unnamed duplicates of the observation interval and
    #   non-negative checks from their first migration; the named checks enforce the same rules.
    source_access = expected['tables']['source_access']
    source_access['columns'] = [column for column in source_access['columns'] if column[0] != 'usage_scope']
    source_access['checks'] = [check for check in source_access['checks'] if check[0] != 'ck_source_access_usage']
    expected['tables']['observations']['checks'] = [check for check in expected['tables']['observations']['checks']
                                                    if check[0] not in ('observations_check', 'observations_normalized_value_check')]
    assert actual == expected

def test_later_migrations_only_add_the_market_data_area(new_database, monkeypatch):
    """Head is the DC1 baseline plus three new tables and one new source_access column, nothing else."""
    baseline_url = migrated(new_database, monkeypatch, BASELINE)
    engine = create_engine(baseline_url)
    try: baseline = describe(engine)
    finally: engine.dispose()
    command.upgrade(Config('alembic.ini'), 'head')
    engine = create_engine(baseline_url)
    try:
        head = describe(engine)
        assert set(inspect(engine).get_table_names()) - CORE_TABLES == MARKET_TABLES | {'alembic_version'}
    finally: engine.dispose()
    added = head['tables']['source_access']['columns'][len(baseline['tables']['source_access']['columns']):]
    assert [column[0] for column in added] == ['export_allowed'] and not added[0][2]
    head['tables']['source_access']['columns'] = head['tables']['source_access']['columns'][:-1]
    assert head == baseline

"""Copy the Data Core tables of an existing MuniQuant database into a new, empty Data Core database.

The source is opened read-only and never changed; a SQLite source is fingerprinted before and after.
The target must be new: a SQLite path that does not exist yet, or a PostgreSQL database without
tables. The tool creates the Core schema there with the Core migrations, copies every Core row
unchanged (same IDs, values, dates and hashes) and compares counts, IDs and per-table fingerprints
of source and target. --dry-run checks the source and writes only the report.

Only the 26 Core tables are read, and only the columns the Core defines. Nothing is dropped: a
column the Core does not define is accepted only while it carries no information, that is, every
value is empty or equals the column's own declared default. A source holding anything else there is
refused.

--exclude FILE leaves out exact rows: a JSON object mapping Core table names to primary keys (a string,
or a list of strings for a composite key). Every listed row must exist, and the copy must stay
consistent without it. The DC1-B split tool uses this to keep material that belongs elsewhere out of
the Core. The report counts the rows left out per table.

--snapshots DIR --target-snapshots NEW_DIR copies the saved page copies of the copied documents and
snapshots into a new directory, each verified against its SHA-256. Without them no files are copied:
point SNAPSHOT_DIR at the source's evidence directory (or a copy of it) when using the target.

    python -m tools.core_import SOURCE TARGET --report REPORT.json [--dry-run] [--exclude FILE]
                                [--snapshots DIR --target-snapshots NEW_DIR]

SOURCE and TARGET are SQLAlchemy URLs or SQLite file paths.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import column, create_engine, inspect, select, table as table_clause, text
from sqlalchemy.engine import make_url
from app.db import make_engine
from app.models import Base
from app.services import normalize_value

ROOT = Path(__file__).resolve().parents[1]
TABLES = [table for table in Base.metadata.sorted_tables]
REFERENCE_TABLES = ('country', 'commodity', 'facility_type')
# Core columns added after the first pilot run, with the value their migration gave existing rows.
LATER_COLUMNS = {('source_access', 'credential_ref'): None, ('source_access', 'auth_header'): None}
STATUSES = ('operating', 'closed', 'suspended', 'planned', 'construction')
# A column default the tool can compare with: a quoted string (optionally cast) or a plain number.
LITERAL_DEFAULT = re.compile(r"^'((?:[^']|'')*)'(?:::[\w ]+)?$|^(-?\d+(?:\.\d+)?)$")

def literal_default(info):
    """The column's declared default when it is a plain literal, else None."""
    match = LITERAL_DEFAULT.match(str(info.get('default') or '').strip())
    if not match: return None
    return match.group(1).replace("''", "'") if match.group(1) is not None else match.group(2)

def location_url(location):
    url = make_url(location if '://' in location else 'sqlite:///' + str(Path(location).resolve()))
    if url.drivername.startswith('sqlite') and (not url.database or url.database == ':memory:'):
        raise ValueError('Use a SQLite file path, not an in-memory database')
    return url

def file_sha256(url):
    if not url.drivername.startswith('sqlite'): return None
    return hashlib.sha256(Path(url.database).read_bytes()).hexdigest()

def open_source(url):
    if url.drivername.startswith('sqlite'):
        path = Path(url.database).resolve()
        if not path.is_file(): raise ValueError('Source database not found: ' + str(path))
        return create_engine(f'sqlite:///file:{path}?mode=ro&uri=true')
    options = (url.query.get('options', '') + ' -c default_transaction_read_only=on').strip()
    return create_engine(url.update_query_dict({'options': options}))

def revision(engine):
    with engine.connect() as connection:
        if 'alembic_version' not in inspect(connection).get_table_names(): return None
        return connection.execute(text('SELECT version_num FROM alembic_version')).scalar()

def canonical(value):
    if isinstance(value, Decimal): return format(value.normalize(), 'f')
    if isinstance(value, float): return repr(value)
    if isinstance(value, (date, datetime)): return value.isoformat()
    return value

def fingerprint(rows):
    content = [[[key, canonical(row[key])] for key in sorted(row)] for row in rows]
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str).encode()).hexdigest()

def identity(table, row):
    return tuple(str(row[column.name]) for column in table.primary_key.columns)

def read_core(connection, check_columns=True, excluded=None):
    """Read every Core row through the Core column types, filling columns added after the pilot.

    Rows whose key is in excluded[table] are left out. Returns the rows, the defaults applied, the
    source columns that are not part of the Core and the number of rows left out per table."""
    present_tables = set(inspect(connection).get_table_names())
    missing = [table.name for table in TABLES if table.name not in present_tables]
    if missing: raise ValueError('Not a MuniQuant database with the Data Core tables; missing: ' + ', '.join(missing))
    excluded = excluded or {}
    data, defaults, extra, left_out = {}, {}, {}, {}
    for table in TABLES:
        skip = excluded.get(table.name, set())
        columns = {info['name']: info for info in inspect(connection).get_columns(table.name)}
        present = set(columns)
        absent = [name for name in table.c.keys() if name not in present]
        unsupported = [name for name in absent if (table.name, name) not in LATER_COLUMNS]
        if check_columns and unsupported: raise ValueError(f'Unsupported source schema: {table.name} lacks ' + ', '.join(unsupported))
        rows, found = [], set()
        for row in connection.execute(select(*[table.c[name] for name in table.c.keys() if name in present])):
            values = dict(row._mapping)
            if identity(table, values) in skip:
                found.add(identity(table, values)); continue
            for name in absent:
                values[name] = LATER_COLUMNS[(table.name, name)]
                defaults[f'{table.name}.{name}'] = LATER_COLUMNS[(table.name, name)]
            rows.append(values)
        # Key order in Python, not SQL collation, so SQLite and PostgreSQL compare identically.
        if skip - found: raise ValueError(f'{table.name}: rows to leave out are not in the source: ' + ', '.join('/'.join(key) for key in sorted(skip - found)[:5]))
        if skip: left_out[table.name] = len(skip)
        data[table.name] = sorted(rows, key=lambda row: identity(table, row))
        # Columns the Core does not define, with the number of copied rows whose value would be
        # lost: neither empty nor the column's own declared default.
        keys = [column(c.name) for c in table.primary_key.columns]
        for name in sorted(present - set(table.c.keys())):
            default = literal_default(columns[name])
            values = connection.execute(select(*keys, column(name)).select_from(table_clause(table.name)))
            extra[f'{table.name}.{name}'] = sum(row[-1] is not None and (default is None or str(row[-1]) != default)
                                                for row in values if tuple(str(key) for key in row[:-1]) not in skip)
    return data, defaults, extra, left_out

def preflight(data, extra):
    """Reject unsafe source data, or data the Core cannot hold, before any target is created."""
    problems = []
    def check(condition, message):
        if not condition: problems.append(message)
    def iso(value):
        try: return date.fromisoformat(value)
        except (TypeError, ValueError): return None
    for column, rows in extra.items():
        check(not rows, f'{column} is not a Core column but holds other values than its default in {rows} rows; split this database with the DC1-B tool')
    for row in data['entities']:
        check(bool(row['country']) and re.fullmatch('[A-Z]{2}', row['country'] or '') is not None, f"entity {row['id']}: invalid country")
        check(row['kind'] != 'facility' or row['facility_type'] in ('smelter', 'refinery', 'bauxite_mine'), f"entity {row['id']}: invalid facility type")
        check(isinstance(row['aliases'], list) and all(isinstance(alias, str) and len(alias) <= 256 for alias in row['aliases']), f"entity {row['id']}: invalid aliases")
    for name in ('observations', 'relationships'):
        for row in data[name]:
            start, end = iso(row['valid_from']), iso(row['valid_to']) if row['valid_to'] else None
            check(start is not None and (row['valid_to'] is None or end is not None), f"{name} {row['id']}: invalid validity date")
            check(not (start and end and end < start), f"{name} {row['id']}: validity interval ends before it starts")
    for row in data['relationships']:
        share = row['percentage']
        check(share is None or (Decimal(str(share)).is_finite() and 0 <= Decimal(str(share)) <= 100), f"relationship {row['id']}: invalid ownership percentage")
    for row in data['observations']:
        if row['attribute'] == 'status':
            check(row['reported_unit'] == 'status' and row['reported_value'] in STATUSES, f"observation {row['id']}: invalid status")
            continue
        try: normalize_value(row['reported_value'], row['reported_unit'], row['attribute'])
        except (ValueError, ArithmeticError) as exc: problems.append(f"observation {row['id']}: unsafe exact numeric value ({exc})")
    for row in data['documents']:
        check(re.fullmatch('[a-f0-9]{64}', row['content_hash'] or '') is not None, f"document {row['id']}: malformed content hash")
        check(not row['published_at'] or iso(row['published_at']) is not None, f"document {row['id']}: invalid publication date")
    # Every reference must point to a copied row; this matters when rows are left out.
    for table in TABLES:
        for key in table.foreign_key_constraints:
            parent, columns = key.referred_table, [c.name for c in key.columns]
            present = {tuple(str(row[e.column.name]) for e in key.elements) for row in data[parent.name]}
            for row in data[table.name]:
                value = tuple(row[name] for name in columns)
                if None not in value and tuple(map(str, value)) not in present:
                    problems.append(f"{table.name} {'/'.join(identity(table, row))} refers to {parent.name} {'/'.join(map(str, value))}, which is not copied")
    if problems: raise ValueError('Correct the source data before import: ' + '; '.join(problems[:20]))

def migrate(url):
    config = Config(str(ROOT / 'alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'migrations'))
    previous = os.environ.get('DATABASE_URL')
    # migrations/env.py reads DATABASE_URL; point it at the new target only for this call.
    os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
    try: command.upgrade(config, 'head')
    finally:
        if previous is None: os.environ.pop('DATABASE_URL', None)
        else: os.environ['DATABASE_URL'] = previous
    return ScriptDirectory.from_config(config).get_current_head()

def require_new_target(url):
    if url.drivername.startswith('sqlite'):
        path = Path(url.database)
        for candidate in (path, Path(str(path) + '-journal'), Path(str(path) + '-wal')):
            if candidate.exists(): raise ValueError('Target must be a new database; refusing existing ' + str(candidate))
        path.parent.mkdir(parents=True, exist_ok=True)
        return
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        if inspector.get_table_names() or inspector.get_view_names(): raise ValueError('Target PostgreSQL database must be empty')
    finally: engine.dispose()

def exclusions(spec):
    """Validate {table: [key, ...]} and return {table: {key tuple}}."""
    names = {table.name: table for table in TABLES}
    if not isinstance(spec, dict): raise ValueError('Rows to leave out must be a JSON object of table names')
    result = {}
    for name, keys in spec.items():
        table = names.get(name)
        if table is None or name in REFERENCE_TABLES: raise ValueError('Cannot leave out rows of ' + str(name))
        width = len(table.primary_key.columns)
        result[name] = set()
        for key in keys if isinstance(keys, list) else [None]:
            key = [key] if isinstance(key, str) else key
            if not isinstance(key, list) or len(key) != width or not all(isinstance(part, str) for part in key):
                raise ValueError(f'{name}: each key must be {width} string(s)')
            result[name].add(tuple(key))
    return result

def snapshot_hashes(data):
    return sorted({row['content_hash'] for row in data['source_snapshot']} | {row['content_hash'] for row in data['documents']})

def check_snapshots(directory, hashes):
    """Return the hashes whose file is missing or does not match its SHA-256."""
    problems = []
    for digest in hashes:
        path = Path(directory) / digest
        if not path.is_file(): problems.append(digest + ': missing')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest: problems.append(digest + ': content does not match')
    return problems

def copy_snapshots(directory, target, hashes):
    target = Path(target)
    target.mkdir(parents=True)
    for digest in hashes:
        shutil.copy2(Path(directory) / digest, target / digest)
    return check_snapshots(target, hashes)

def copy(source, target, dry_run=False, exclude=None, snapshots=None, target_snapshots=None):
    """Copy Core rows from source to a new target; return the comparison report."""
    source_url, target_url = location_url(source), location_url(target)
    if source_url.render_as_string(hide_password=False) == target_url.render_as_string(hide_password=False):
        raise ValueError('Source and target must differ')
    if (snapshots is None) != (target_snapshots is None): raise ValueError('Give both the snapshot directory and the new target directory')
    if target_snapshots is not None and Path(target_snapshots).exists(): raise ValueError('Target snapshot directory must be new')
    excluded = exclusions(exclude or {})
    before = file_sha256(source_url)
    engine = open_source(source_url)
    try:
        source_revision = revision(engine)
        with engine.connect() as connection: data, defaults, extra, left_out = read_core(connection, excluded=excluded)
    finally: engine.dispose()
    preflight(data, extra)
    report = {'tool': 'tools.core_import', 'mode': 'dry-run' if dry_run else 'copy',
              'source': {'url': source_url.render_as_string(hide_password=True), 'revision': source_revision, 'sha256_before': before},
              'target': {'url': target_url.render_as_string(hide_password=True)},
              'defaults_applied': defaults, 'source_columns_not_in_core': extra, 'rows_left_out': left_out, 'tables': {}}
    for table in TABLES:
        rows = data[table.name]
        report['tables'][table.name] = {'source_rows': len(rows), 'source_fingerprint': fingerprint(rows)}
    hashes = snapshot_hashes(data)
    if snapshots is not None:
        problems = check_snapshots(snapshots, hashes)
        report['snapshots'] = {'source': str(snapshots), 'files': len(hashes), 'problems': problems}
        if problems: raise ValueError('Saved page copies are missing or damaged: ' + '; '.join(problems[:5]))
    if dry_run:
        report['status'] = 'DRY_RUN_OK'
    else:
        require_new_target(target_url)
        created = target_url.drivername.startswith('sqlite')
        snapshots_created = False
        try:
            report['target']['revision'] = migrate(target_url)
            target_engine = make_engine(target_url.render_as_string(hide_password=False))
            try:
                with target_engine.begin() as connection:
                    existing, _, _, _ = read_core(connection, check_columns=False)
                    for table in TABLES:
                        rows = data[table.name]
                        if table.name in REFERENCE_TABLES:
                            seeded = {row['code']: row for row in existing[table.name]}
                            conflicts = [row['code'] for row in rows if row['code'] in seeded and seeded[row['code']] != row]
                            if conflicts: raise ValueError(f'{table.name} reference rows differ from the Core registry: ' + ', '.join(conflicts))
                            rows = [row for row in rows if row['code'] not in seeded]
                            report['tables'][table.name]['seeded_by_baseline'] = len(seeded)
                        elif existing[table.name]: raise ValueError('Target is not empty: ' + table.name)
                        if rows: connection.execute(table.insert(), rows)
                with target_engine.connect() as connection: copied, _, _, _ = read_core(connection)
            finally: target_engine.dispose()
            for table in TABLES:
                expected, actual = data[table.name], copied[table.name]
                if table.name in REFERENCE_TABLES:
                    # The baseline seeds the registry; the source's rows must all be present unchanged.
                    present = {row['code']: row for row in actual}
                    equal = all(present.get(row['code']) == row for row in expected)
                    actual = [present[row['code']] for row in expected if row['code'] in present]
                else:
                    equal = [identity(table, row) for row in expected] == [identity(table, row) for row in actual]
                entry = report['tables'][table.name]
                entry.update({'target_rows': len(copied[table.name]), 'ids_equal': equal,
                              'target_fingerprint': fingerprint(actual)})
                entry['equal'] = equal and entry['target_fingerprint'] == entry['source_fingerprint']
            if snapshots is not None:
                snapshots_created = True
                report['snapshots'].update({'target': str(target_snapshots), 'target_problems': copy_snapshots(snapshots, target_snapshots, hashes)})
        except Exception:
            if created: Path(target_url.database).unlink(missing_ok=True)
            if snapshots_created: shutil.rmtree(target_snapshots, ignore_errors=True)
            raise
        report['status'] = 'PASS' if all(entry['equal'] for entry in report['tables'].values()) and not report.get('snapshots', {}).get('target_problems') else 'FAIL'
    after = file_sha256(source_url)
    report['source'].update({'sha256_after': after, 'unchanged': before == after})
    if not report['source']['unchanged']: report['status'] = 'FAIL'
    return report

def compare(source, target):
    """Compare the Core rows of a source database with an existing Core database; both are only read.

    Used to check a Core database another tool made (DC1-B4): same counts, IDs and fingerprints."""
    source_url, target_url = location_url(source), location_url(target)
    before = {'source': file_sha256(source_url), 'target': file_sha256(target_url)}
    tables = {}
    for name, url in (('source', source_url), ('target', target_url)):
        engine = open_source(url)
        try:
            with engine.connect() as connection: tables[name], _, extra, _ = read_core(connection, check_columns=name == 'target')
        finally: engine.dispose()
    report = {'tool': 'tools.core_import compare', 'source': {'url': source_url.render_as_string(hide_password=True)},
              'target': {'url': target_url.render_as_string(hide_password=True)}, 'tables': {}}
    for table in TABLES:
        expected, actual = tables['source'][table.name], tables['target'][table.name]
        if table.name in REFERENCE_TABLES:
            present = {row['code']: row for row in actual}
            equal = all(present.get(row['code']) == row for row in expected)
            actual = [present[row['code']] for row in expected if row['code'] in present]
        else:
            equal = [identity(table, row) for row in expected] == [identity(table, row) for row in actual]
        entry = {'source_rows': len(expected), 'target_rows': len(tables['target'][table.name]), 'ids_equal': equal,
                 'source_fingerprint': fingerprint(expected), 'target_fingerprint': fingerprint(actual)}
        entry['equal'] = equal and entry['source_fingerprint'] == entry['target_fingerprint']
        report['tables'][table.name] = entry
    for name, url in (('source', source_url), ('target', target_url)):
        after = file_sha256(url)
        report[name].update({'sha256_before': before[name], 'sha256_after': after, 'unchanged': before[name] == after})
    report['status'] = 'PASS' if all(entry['equal'] for entry in report['tables'].values()) and report['source']['unchanged'] and report['target']['unchanged'] else 'FAIL'
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source'); parser.add_argument('target')
    parser.add_argument('--report', required=True, type=Path, help='new JSON report path')
    parser.add_argument('--dry-run', action='store_true', help='check the source and write the report only')
    parser.add_argument('--exclude', type=Path, help='JSON file of rows to leave out: {"table": ["key", ...]}')
    parser.add_argument('--snapshots', type=Path, help="the source's snapshot directory")
    parser.add_argument('--target-snapshots', type=Path, help='new directory for the copied snapshot files')
    args = parser.parse_args()
    if args.report.exists(): parser.error('Report path already exists; choose a new one')
    exclude = json.loads(args.exclude.read_text()) if args.exclude else None
    report = copy(args.source, args.target, args.dry_run, exclude, args.snapshots, args.target_snapshots)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x') as stream: json.dump(report, stream, indent=2)
    print(json.dumps({'status': report['status'], 'report': str(args.report)}))
    raise SystemExit(0 if report['status'] in ('PASS', 'DRY_RUN_OK') else 1)

if __name__ == '__main__': main()

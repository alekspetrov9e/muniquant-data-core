"""Export and replay the real-source pilot baseline inside the Data Core and compare with its own results.

DC1 steps A6 and B4. The baseline is a real-source pilot captured on 2026-10-21 by the platform at
commit 26a0bcd. The files of the 10 October 2026 pilot were lost, and the team approved this fresh
run as the baseline instead. Its manifest fingerprint and build hash are pinned below; the files
hold copies of third-party pages, so they stay out of git in data/pilot-baseline-2026-10-21.

Inputs, all required (defaults: the baseline):
  --database    pilot SQLite database               (real-pilot.db)
  --snapshots   pilot snapshot directory            (real-pilot-snapshots)
  --export-dir  pilot output directory with pilot-evidence-package.json,
                pilot-frozen-evidence.zip and pilot-validation.json (real-pilot-export)
  --manifest    JSON {"files": {"relative/path": "sha256"}}, paths relative to the manifest;
                it must cover the database, the three output files and every referenced snapshot
--output must be a new directory. It receives the Core database, the Core export and frozen
bundle, report.json and report.md. The inputs are only read.

PASS       the Core export is byte-identical, frozen replay and recipe are equal, matching
           decisions and quality counts are the same.
DIFFERENT  anything differs. The step stops; the report lists every difference.
BLOCKED    an input is missing, the manifest is not the recorded one, or a file does not match
           its manifest fingerprint. The comparison with the baseline is then not established.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.contract import export_v1, freeze_v1, replay_v1, validate_package
from app.db import make_engine
from app.models import Candidate, Document, Entity, Review, Source
from app.quality import inspect_quality
from app.services import record
from tools import core_import

BASELINE = Path('data/pilot-baseline-2026-10-21')
BASELINE_BUILD_HASH = '878944013542732000b9efaa80b714d4aeb8e35abac9fa84506b165ca668695e'
BASELINE_MANIFEST_SHA256 = '1466d814d3210f1134e2eab1dca89bba77928152928d54735ec6d42a28b4871f'
BASELINE_WARNINGS = 11
OUTPUTS = ('pilot-evidence-package.json', 'pilot-frozen-evidence.zip', 'pilot-validation.json')
SECTIONS = {'records': 'record_id', 'entities': 'external_entity_id', 'relationships': 'relationship_id',
            'sources': 'source_id', 'documents': 'document_id', 'build_manifest': 'build_id'}

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def item_differences(label, expected, actual, key):
    """Field-by-field differences between two lists of records identified by key."""
    differences = []
    if not isinstance(key, str):
        expected, actual = {key(item): item for item in expected}, {key(item): item for item in actual}
    else:
        expected, actual = {item[key]: item for item in expected}, {item[key]: item for item in actual}
    for identifier in sorted(set(expected) | set(actual), key=str):
        if identifier not in actual: differences.append(f'{label} {identifier}: missing in the Core'); continue
        if identifier not in expected: differences.append(f'{label} {identifier}: only in the Core'); continue
        for field in sorted(set(expected[identifier]) | set(actual[identifier])):
            old, new = expected[identifier].get(field), actual[identifier].get(field)
            if old != new: differences.append(f'{label} {identifier}.{field}: pilot {old!r} != Core {new!r}')
    return differences

def package_differences(expected, actual):
    differences = []
    for section in sorted(set(expected) | set(actual)):
        if section in SECTIONS:
            differences += item_differences(section, expected.get(section, []), actual.get(section, []), SECTIONS[section])
        elif section == 'identity_evidence':
            differences += item_differences(section, expected.get(section, []), actual.get(section, []), lambda item: (item['external_entity_id'], item['document_id']))
        elif expected.get(section) != actual.get(section):
            differences.append(f'package {section}: pilot {expected.get(section)!r} != Core {actual.get(section)!r}')
    return differences

def recipe(bundle):
    with zipfile.ZipFile(bundle) as archive:
        snapshots = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith('snapshots/')}
        return json.loads(archive.read('recipe.json')), snapshots

def inputs_status(args):
    """Return (problems, fingerprints) for presence and manifest coverage of every input."""
    problems, fingerprints = [], {}
    database, snapshots, outputs = Path(args.database), Path(args.snapshots), [Path(args.export_dir) / name for name in OUTPUTS]
    for path, kind in [(database, 'pilot database'), (snapshots, 'snapshot directory'), *[(path, 'pilot output') for path in outputs], (Path(args.manifest), 'manifest')]:
        if not path.exists(): problems.append(f'missing input: {kind} {path}')
    if problems: return problems, fingerprints
    manifest_path = Path(args.manifest)
    fingerprints['manifest'] = sha256(manifest_path)
    expected = getattr(args, 'expected_manifest', None)
    if expected and fingerprints['manifest'] != expected:
        return [f"manifest {manifest_path} is not the recorded one (SHA-256 {fingerprints['manifest']}, recorded {expected})"], fingerprints
    try: listed = json.loads(manifest_path.read_text())['files']
    except (ValueError, KeyError, TypeError): return ['manifest is not a {"files": {path: sha256}} document'], fingerprints
    base = manifest_path.parent.resolve()
    verified = {}
    for name, expected in listed.items():
        path = (base / name).resolve()
        if not path.is_file(): problems.append(f'manifest file missing: {name}'); continue
        actual = sha256(path)
        if actual != expected: problems.append(f'fingerprint mismatch: {name} (manifest {expected}, file {actual})')
        verified[path] = actual
    required = [database.resolve(), *[path.resolve() for path in outputs]]
    engine = core_import.open_source(core_import.location_url(str(database)))
    try:
        with engine.connect() as connection:
            hashes = sorted(set(connection.execute(select(Document.content_hash)).scalars()))
    finally: engine.dispose()
    required += [(snapshots / digest).resolve() for digest in hashes]
    for path in required:
        if path not in verified: problems.append(f'input not covered by the manifest: {path}')
    fingerprints['files'] = {str(path): digest for path, digest in sorted(verified.items(), key=lambda item: str(item[0]))}
    return problems, fingerprints

def compare(args):
    output = Path(args.output)
    checks, differences = [], []
    def check(name, passed, detail=''):
        checks.append({'check': name, 'passed': bool(passed), 'detail': detail})
        return passed
    problems, fingerprints = inputs_status(args)
    report = {'tool': 'tools.compare_pilot', 'expected_build_hash': args.expected_hash, 'inputs': fingerprints}
    if problems:
        report.update({'status': 'BLOCKED', 'problems': problems,
                       'conclusion': 'Blocked: missing or unverified input. The comparison with the old pilot result is not established.'})
        return report
    export_dir = Path(args.export_dir)
    reference_bytes = (export_dir / 'pilot-evidence-package.json').read_bytes()
    reference = json.loads(reference_bytes)
    reference_bundle = export_dir / 'pilot-frozen-evidence.zip'
    validation = json.loads((export_dir / 'pilot-validation.json').read_text())
    # 1. The pilot's own artifacts are valid under the Core contract and carry the recorded hash.
    try:
        validate_package(json.loads(reference_bytes)); valid = True
    except Exception as exc: valid = False; differences.append(f'pilot package fails Core contract validation: {exc}')
    check('Pilot package passes the Core contract validator', valid)
    check('Pilot package carries the recorded build hash', reference['build_hash'] == args.expected_hash, reference['build_hash'])
    # 2. Replay the frozen pilot bundle inside the Core.
    try: replayed = replay_v1(reference_bundle)
    except Exception as exc: replayed = {'equivalent': False, 'error': str(exc)}
    check('Frozen pilot bundle replays equivalently in the Core', replayed.get('equivalent') and replayed.get('build_hash') == args.expected_hash, json.dumps(replayed))
    reference_recipe, reference_snapshots = recipe(reference_bundle)
    check('Frozen bundle package equals the pilot package', reference_recipe['package'] == reference)
    # 3. Copy the pilot's Core tables into a new Core database (the pilot database is only read).
    output.mkdir(parents=True)
    core_db = output / 'core.db'
    try: imported = core_import.copy(str(args.database), str(core_db))
    except Exception as exc:
        differences.append(f'Core import of the pilot database failed: {exc}')
        check('Pilot rows copied unchanged into the Core (counts, IDs, fingerprints)', False, str(exc)[:200])
        report.update({'status': 'DIFFERENT', 'checks': checks, 'differences': differences,
                       'conclusion': 'Differences found: the step stops for a joint review.'})
        return report
    (output / 'import-report.json').write_text(json.dumps(imported, indent=2))
    check('Pilot rows copied unchanged into the Core (counts, IDs, fingerprints)', imported['status'] == 'PASS', 'see import-report.json')
    check('Pilot database unchanged by the comparison', imported['source']['unchanged'], imported['source']['sha256_after'])
    engine = make_engine('sqlite:///' + str(core_db.resolve()))
    try:
        with Session(engine) as s:
            # 4. Quality: the pilot was WARN with the recorded number of warnings and no BLOCK/ERROR.
            quality = inspect_quality(s, args.snapshots)
            counts = quality['counts']
            check('Quality status and counts match the pilot', quality['status'] == 'WARN' and counts.get('WARN', 0) == args.expected_warnings and not counts.get('BLOCK') and not counts.get('ERROR'), json.dumps(counts))
            # 5. Export inside the Core; byte-identical to the file the pilot wrote.
            try: package = export_v1(s, args.snapshots)
            except Exception as exc: package = None; differences.append(f'Core export failed: {exc}')
            if package is not None:
                core_bytes = json.dumps(package, indent=2).encode()
                (output / 'core-evidence-package.json').write_bytes(core_bytes)
                check('Core export is byte-identical to the pilot export', core_bytes == reference_bytes, hashlib.sha256(core_bytes).hexdigest())
                check('Core export build hash equals the recorded pilot hash', package['build_hash'] == args.expected_hash, package['build_hash'])
                field_differences = package_differences(reference, package)
                differences += field_differences
                check('Every record has the same fact IDs, values, units, dates and evidence fingerprints', not field_differences, f'{len(field_differences)} field differences')
            # 6. Matching decisions: candidates and human reviews, field by field.
            decisions = item_differences('candidate', reference_recipe['candidates'], [record(c) for c in s.scalars(select(Candidate).order_by(Candidate.id))], 'id')
            decisions += item_differences('review', reference_recipe['reviews'], [record(r) for r in s.scalars(select(Review).order_by(Review.id))], 'id')
            differences += decisions
            check('Matching decisions are the same (candidates and reviews)', not decisions, f'{len(decisions)} differences')
            # 7. Freeze inside the Core and replay offline; the recipe must equal the pilot's.
            if package is not None:
                core_bundle = output / 'core-frozen-evidence.zip'
                freeze_v1(s, args.snapshots, core_bundle)
                core_replay = replay_v1(core_bundle)
                core_recipe, core_snapshots = recipe(core_bundle)
                check('Core frozen bundle replays equivalently', core_replay['equivalent'] and core_replay['build_hash'] == args.expected_hash, json.dumps(core_replay))
                check('Core frozen recipe equals the pilot recipe', core_recipe['recipe_hash'] == reference_recipe['recipe_hash'], core_recipe['recipe_hash'])
                check('Core frozen bundle holds the same snapshot bytes', core_snapshots == reference_snapshots, f'{len(core_snapshots)} snapshots')
                recipe_differences = item_differences('build', reference_recipe['builds'], core_recipe['builds'], 'id')
                recipe_differences += item_differences('frozen entity', reference_recipe['entities'], core_recipe['entities'], 'id')
                differences += recipe_differences
                # 8. The pilot's summary numbers.
                facilities = s.scalars(select(Entity).where(Entity.kind == 'facility')).all()
                companies = s.scalars(select(Entity).where(Entity.kind == 'company')).all()
                derived = {'facilities': len(facilities), 'company_records': len(companies), 'source_families': len(s.scalars(select(Source)).all()),
                           'source_urls': len(set(s.scalars(select(Document.original_url)))), 'registered_documents': len(package['documents']),
                           'parsed_capacity_observations': len(package['records']), 'relationships': len(package['relationships']),
                           'build_hash': package['build_hash'], 'replay': core_replay}
                summary = [f'pilot-validation {key}: pilot {validation.get(key)!r} != Core {value!r}' for key, value in derived.items() if validation.get(key) != value]
                differences += summary
                check("Pilot summary numbers match the Core's", not summary, json.dumps({key: derived[key] for key in derived if key != 'replay'}))
    finally: engine.dispose()
    status = 'PASS' if all(item['passed'] for item in checks) and not differences else 'DIFFERENT'
    report.update({'status': status, 'checks': checks, 'differences': differences,
                   'conclusion': 'Same result as the pilot.' if status == 'PASS' else 'Differences found: the step stops for a joint review.'})
    return report

def markdown(report):
    lines = ['# Pilot comparison inside the Data Core', '', f"Status: **{report['status']}**", '', report['conclusion'], '',
             f"Expected build hash: `{report['expected_build_hash']}`", '']
    if report.get('problems'):
        lines += ['## Problems', ''] + [f'- {problem}' for problem in report['problems']] + ['']
    if report.get('checks'):
        lines += ['## Checks', '', '| Check | Result | Detail |', '|---|---|---|']
        lines += [f"| {item['check']} | {'pass' if item['passed'] else 'FAIL'} | {item['detail'][:120]} |" for item in report['checks']] + ['']
    if report.get('differences'):
        lines += ['## Differences', ''] + [f'- {item}' for item in report['differences']] + ['']
    if report['inputs'].get('files'):
        lines += ['## Input fingerprints', '', f"Manifest: `{report['inputs']['manifest']}`", ''] + [f'- `{digest}` {path}' for path, digest in report['inputs']['files'].items()] + ['']
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--database', default=str(BASELINE / 'real-pilot.db'))
    parser.add_argument('--snapshots', default=str(BASELINE / 'real-pilot-snapshots'))
    parser.add_argument('--export-dir', default=str(BASELINE / 'real-pilot-export'))
    parser.add_argument('--manifest', default=str(BASELINE / 'manifest.json'))
    parser.add_argument('--expected-manifest', default=BASELINE_MANIFEST_SHA256, help="the manifest's own SHA-256; empty to skip")
    parser.add_argument('--expected-hash', default=BASELINE_BUILD_HASH)
    parser.add_argument('--expected-warnings', type=int, default=BASELINE_WARNINGS, help='WARN findings recorded for the pilot')
    parser.add_argument('--output', required=True, type=Path, help='new directory for the Core results and the report')
    args = parser.parse_args()
    if args.output.exists(): parser.error('Output directory already exists; choose a new one')
    report = compare(args)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2))
    (args.output / 'report.md').write_text(markdown(report))
    print(json.dumps({'status': report['status'], 'report': str(args.output / 'report.md')}))
    raise SystemExit({'PASS': 0, 'DIFFERENT': 1, 'BLOCKED': 3}[report['status']])

if __name__ == '__main__': main()

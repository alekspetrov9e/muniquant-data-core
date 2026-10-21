"""DC1 step A6 tooling: tools/compare_pilot.py proven on the pilot-shaped fixture made by the pilot code.

These tests prove the comparison works. They do not replace the real-source baseline that A6
runs against (docs/A6-PILOT-COMPARISON.md).
"""
import hashlib
import json
import sqlite3
from argparse import Namespace
from pathlib import Path
from tools import compare_pilot
from test_core_import import restore_pilot_shaped

FIXTURE_HASH = 'd0df265b56abbb4d3f0f0e49651147b71f3ed7e8f012bb0753184be3bfee8a6f'

def inputs(tmp_path, manifest=True, change=None):
    database = restore_pilot_shaped(tmp_path)
    if change:
        with sqlite3.connect(database) as connection: connection.execute(change)
    if manifest:
        files = [database, *sorted((tmp_path / 'real-pilot-snapshots').iterdir()), *sorted((tmp_path / 'real-pilot-export').iterdir())]
        listed = {str(path.relative_to(tmp_path)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
        (tmp_path / 'manifest.json').write_text(json.dumps({'files': listed}))
    return Namespace(database=str(database), snapshots=str(tmp_path / 'real-pilot-snapshots'), export_dir=str(tmp_path / 'real-pilot-export'),
                     manifest=str(tmp_path / 'manifest.json'), expected_hash=FIXTURE_HASH, expected_warnings=7, output=str(tmp_path / 'result'))

def test_core_reproduces_the_pilot_code_results(tmp_path):
    report = compare_pilot.compare(inputs(tmp_path))
    assert report['status'] == 'PASS', report
    assert all(check['passed'] for check in report['checks']) and not report['differences']
    names = {check['check'] for check in report['checks']}
    assert 'Core export is byte-identical to the pilot export' in names
    assert 'Matching decisions are the same (candidates and reviews)' in names
    assert (tmp_path / 'result' / 'core-evidence-package.json').read_bytes() == (tmp_path / 'real-pilot-export' / 'pilot-evidence-package.json').read_bytes()

def test_any_core_difference_stops_the_step(tmp_path, monkeypatch):
    original = compare_pilot.export_v1
    def regressed(session, storage):
        package = original(session, storage)
        package['records'][0]['normalized_value'] = '1'
        return package
    monkeypatch.setattr(compare_pilot, 'export_v1', regressed)
    report = compare_pilot.compare(inputs(tmp_path))
    assert report['status'] == 'DIFFERENT'
    assert any('.normalized_value: pilot' in difference for difference in report['differences'])

def test_missing_inputs_block_the_comparison(tmp_path):
    report = compare_pilot.compare(inputs(tmp_path, manifest=False))
    assert report['status'] == 'BLOCKED' and 'not established' in report['conclusion']
    assert any('manifest' in problem for problem in report['problems'])
    assert not (tmp_path / 'result').exists()

def test_unverified_inputs_block_the_comparison(tmp_path):
    args = inputs(tmp_path)
    snapshot = sorted(Path(args.snapshots).iterdir())[0]
    snapshot.write_bytes(snapshot.read_bytes() + b' ')
    report = compare_pilot.compare(args)
    assert report['status'] == 'BLOCKED' and any('fingerprint mismatch' in problem for problem in report['problems'])

def test_a_pilot_database_the_core_cannot_load_is_a_difference(tmp_path):
    report = compare_pilot.compare(inputs(tmp_path, change="UPDATE observations SET reported_value='NaN' WHERE attribute='capacity'"))
    assert report['status'] == 'DIFFERENT'
    assert any('Core import of the pilot database failed' in item for item in report['differences'])

def test_a_manifest_other_than_the_recorded_one_blocks(tmp_path):
    args = inputs(tmp_path)
    args.expected_manifest = '0' * 64
    report = compare_pilot.compare(args)
    assert report['status'] == 'BLOCKED' and any('not the recorded one' in problem for problem in report['problems'])

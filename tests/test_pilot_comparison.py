"""DC1 step A6 tooling: tools/compare_pilot.py proven on the pilot-shaped fixture made by the pilot code.

These tests prove the comparison works. They do not replace the real pilot: A6 itself stays
blocked until the real 10 October database, snapshots, manifest and frozen bundle are supplied.
"""
import hashlib
import json
from argparse import Namespace
from pathlib import Path
from tools import compare_pilot
from test_core_import import restore_pilot_shaped

FIXTURE_HASH = 'd0df265b56abbb4d3f0f0e49651147b71f3ed7e8f012bb0753184be3bfee8a6f'

def inputs(tmp_path, manifest=True):
    database = restore_pilot_shaped(tmp_path)
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

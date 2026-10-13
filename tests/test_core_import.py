"""tools/core_import.py: read-only source, new targets only, dry run, and a verified report."""
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
import pytest
from sqlalchemy import text
from tools import core_import

PILOT_SHAPED = Path(__file__).parent / 'fixtures' / 'pilot-shaped'

def restore_pilot_shaped(tmp_path):
    database = tmp_path / 'real-pilot.db'
    with sqlite3.connect(database) as connection: connection.executescript((PILOT_SHAPED / 'database.sql').read_text())
    shutil.copytree(PILOT_SHAPED / 'real-pilot-snapshots', tmp_path / 'real-pilot-snapshots')
    shutil.copytree(PILOT_SHAPED / 'real-pilot-export', tmp_path / 'real-pilot-export')
    return database

def source_url(client):
    return client.app.state.engine.url.render_as_string(hide_password=False)

def test_dry_run_reports_without_creating_the_target(client, example, tmp_path):
    entity, _, doc, _ = example
    client.post('/api/observations', json={'entity_id': entity['id'], 'document_id': doc['id'], 'reported_value': '400', 'reported_unit': 'kt/year', 'valid_from': '2025-01-01', 'evidence_reference': 'table 1'})
    report = core_import.copy(source_url(client), str(tmp_path / 'never.db'), dry_run=True)
    assert report['status'] == 'DRY_RUN_OK' and not (tmp_path / 'never.db').exists()
    assert report['tables']['observations']['source_rows'] == 1 and report['source']['unchanged']

def test_copy_keeps_every_row_and_verifies_it(client, example, new_database):
    report = core_import.copy(source_url(client), new_database('copy'))
    assert report['status'] == 'PASS' and report['target']['revision']
    assert all(entry['equal'] for entry in report['tables'].values()) and len(report['tables']) == 26
    assert report['tables']['country']['seeded_by_baseline'] == 28

def test_refuses_targets_that_are_not_new(client, example, new_database, tmp_path):
    target = new_database('used')
    assert core_import.copy(source_url(client), target)['status'] == 'PASS'
    with pytest.raises(ValueError, match='new database|must be empty'):
        core_import.copy(source_url(client), target)
    with pytest.raises(ValueError, match='differ'):
        core_import.copy(source_url(client), source_url(client))

def test_refuses_hint_only_workspace_material(client, example, new_database):
    _, source, _, _ = example
    policy = {'status': 'permitted', 'allowed_hosts': ['example.org'], 'basis': 'Fixture access decision for tests', 'retention': 'Fixture only'}
    assert client.post('/api/sources/' + source['id'] + '/access', json=policy).status_code == 201
    # The monolith marks lead feeds in source_access.usage_scope; such databases are split in DC1-B.
    with client.app.state.engine.begin() as connection:
        connection.execute(text("ALTER TABLE source_access ADD COLUMN usage_scope VARCHAR DEFAULT 'evidence' NOT NULL"))
        connection.execute(text("UPDATE source_access SET usage_scope='leads_only'"))
    with pytest.raises(ValueError, match='hint-only material stays with the Workspace'):
        core_import.copy(source_url(client), new_database('refused'))

def test_pilot_era_database_is_copied_unchanged(tmp_path):
    database = restore_pilot_shaped(tmp_path)
    report = core_import.copy(str(database), str(tmp_path / 'core.db'))
    assert report['status'] == 'PASS' and report['source']['revision'] == 'fcf5b3d9e812'
    assert report['defaults_applied'] == {'source_access.credential_ref': None, 'source_access.auth_header': None}
    assert report['source']['sha256_before'] == report['source']['sha256_after']

def test_command_line_writes_a_report_and_refuses_overwrites(tmp_path):
    database = restore_pilot_shaped(tmp_path)
    command = [sys.executable, '-m', 'tools.core_import', str(database), str(tmp_path / 'cli.db'), '--report', str(tmp_path / 'report.json')]
    result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / 'report.json').read_text())['status'] == 'PASS'
    assert subprocess.run(command, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True).returncode != 0

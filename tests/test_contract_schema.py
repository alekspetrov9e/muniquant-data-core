"""DC1 step A4: CommodityEvidencePackage 1.0.0 is unchanged and its forbidden-field checks stay."""
import hashlib
import runpy
import shutil
from pathlib import Path
from app.contract import PROHIBITED, SCHEMA, VERSION

ROOT = Path(__file__).resolve().parents[1]
# SHA-256 of app/evidence-v1.schema.json in the platform since the 1.0.0 release (commit 56cfa78, 2026-10-10).
SCHEMA_SHA256 = '7808149a3e26e28ca18472d88c293f4d088b08ff40ecdaf7e7428c736fb4151f'

def test_schema_file_is_byte_for_byte_the_released_one():
    assert hashlib.sha256(SCHEMA.read_bytes()).hexdigest() == SCHEMA_SHA256
    assert VERSION == '1.0.0'

def test_schema_generator_reproduces_the_file(tmp_path, monkeypatch):
    shutil.copy(ROOT / 'scripts' / 'export_v1_schema.py', tmp_path)
    (tmp_path / 'app').mkdir()
    monkeypatch.chdir(tmp_path)
    runpy.run_path('export_v1_schema.py')
    assert (tmp_path / 'app' / 'evidence-v1.schema.json').read_bytes() == SCHEMA.read_bytes()

def test_forbidden_field_list_is_unchanged():
    assert PROHIBITED == {'impact_score', 'surprise_score', 'market_state', 'analogue_score', 'supply_pressure',
                          'price_prediction', 'procurement_signal', 'trading_signal', 'factor_weight', 'alpha'}

def test_api_serves_the_same_schema_bytes(client):
    assert client.get('/api/export/schema').content == SCHEMA.read_bytes()

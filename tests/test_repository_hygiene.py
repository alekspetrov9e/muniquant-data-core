"""DC1 step A7: no passwords, licensed data or copies of third-party pages in the repository.

The gitleaks secret scan in CI covers credentials in all files and history. These checks cover the
rest: every stored page must be a declared synthetic fixture verified by its manifest.
"""
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = [ROOT / 'fixtures' / 'demo' / 'manifest.json', ROOT / 'tests' / 'fixtures' / 'pilot-shaped' / 'manifest.json']
SKIP = {'.git', '.venv', 'data', '__pycache__', '.pytest_cache'}

def repository_files():
    try:
        listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        return [ROOT / name for name in listed if (ROOT / name).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [path for path in ROOT.rglob('*') if path.is_file() and not SKIP & set(path.relative_to(ROOT).parts)]

def test_no_secrets_databases_documents_or_local_data():
    names = [path.relative_to(ROOT) for path in repository_files()]
    assert not [name for name in names if name.name == '.env' or name.suffix in ('.db', '.sqlite', '.pdf', '.dump') or name.parts[0] == 'data']

def test_environment_template_holds_placeholders_only():
    for line in (ROOT / '.env.example').read_text().splitlines():
        if not line or line.startswith('#'): continue
        name, value = line.split('=', 1)
        assert value in ('', 'false') or value.startswith('replace-with-') or (name == 'WRITE_ACTOR' and re.fullmatch('[a-z-]+', value)), line

def test_fixture_manifests_match_and_declare_synthetic_data():
    for manifest in MANIFESTS:
        content = json.loads(manifest.read_text())
        assert content['synthetic'] is True
        for name, digest in content['files'].items():
            assert hashlib.sha256((manifest.parent / name).read_bytes()).hexdigest() == digest, name

def test_every_stored_page_is_a_declared_synthetic_fixture():
    declared = {(manifest.parent / name).resolve() for manifest in MANIFESTS for name in json.loads(manifest.read_text())['files']}
    pages = [path for path in repository_files() if 'snapshots' in path.parent.name]
    assert pages
    for path in pages:
        assert path.resolve() in declared, path
        assert b'synthetic' in path.read_bytes().lower(), path
    for bundle in [path for path in repository_files() if path.suffix == '.zip']:
        assert bundle.resolve() in declared, bundle
        with zipfile.ZipFile(bundle) as archive:
            for name in archive.namelist():
                if name.startswith('snapshots/'): assert b'synthetic' in archive.read(name).lower(), (bundle, name)

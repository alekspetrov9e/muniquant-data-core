"""DC1 step A3: one way only. No Core file uses a Workspace file, class, table, route or screen.

The Workspace knows the Core; the Core does not know the Workspace. The names below are the
Workspace's modules, classes, tables, routes and scripts in the platform on 2026-10-13 (commit
1f02c0b). This file is the only place allowed to list them.
"""
import ast
import importlib
import pkgutil
import re
import subprocess
import sys
from pathlib import Path
import app
from app.models import Base

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_MODULES = {'research', 'research_models', 'research_schemas', 'research_demo', 'permutable', 'investigations',
                     'asset_map', 'chatbot', 'event_influence', 'event_search', 'paper_performance'}
WORKSPACE_CLASSES = {'MarketObservation', 'PaperAccount', 'PaperOrder', 'Lead', 'LeadRevision', 'LeadHeadline',
                     'ResearchEvent', 'ResearchQuote', 'ResearchOutcome', 'PaperPolicy', 'PaperDecision',
                     'Investigation', 'InvestigationRevision', 'InvestigationEntry', 'InvestigationTask',
                     'InvestigationTaskEvidence', 'AssetLocation', 'AssetDependency', 'PermutableSourceIn',
                     'PermutableCaptureIn', 'LeadDecisionIn', 'CaseIn', 'RevisionIn', 'LocationIn', 'DependencyIn',
                     'ChatIn', 'EventIn', 'QuoteIn', 'OutcomeIn', 'PolicyIn', 'LeadConflict', 'CaseConflict'}
WORKSPACE_TABLES = {'market_observations', 'paper_accounts', 'paper_orders', 'lead', 'lead_revision', 'lead_headline',
                    'research_event', 'research_quote', 'research_outcome', 'paper_policy', 'research_paper_account',
                    'research_paper_decision', 'investigation', 'investigation_revision', 'investigation_entry',
                    'investigation_task', 'investigation_task_evidence', 'asset_location', 'asset_dependency'}
WORKSPACE_ROUTES = ('/api/leads', '/api/permutable', '/api/research', '/api/investigations', '/api/asset-map',
                    '/api/chat', '/market-chart', '/asset-map-view', '/api/export/draft')
WORKSPACE_SCRIPTS = ('market.js', 'chatbot.js', 'chatbot.css', 'investigations.js', 'asset-map', 'leaflet', 'tradingview')
# Runtime identifiers may not name Workspace features (free text such as a User-Agent is not code).
WORKSPACE_WORDS = re.compile(r'lead|research|investigat|permutable|paper|asset_?map|chat|trading|market|influence', re.I)
# The frozen 0.1.0-draft package format has an always-empty market_observations field; the legacy
# draft tool must keep it to read and verify old draft bundles. It is a format field, not a table.
ALLOWED = {('tools/legacy_bundle.py', 'names market_observations')}

def python_files():
    skip = {ROOT / 'tests' / 'test_boundary.py', ROOT / 'tests' / 'fixtures' / 'pilot-shaped' / 'generate.py'}
    return [path for path in ROOT.rglob('*.py') if '.venv' not in path.parts and path not in skip and 'site-packages' not in path.parts]

def violations(source, runtime=False, strings=True):
    """Workspace references in one Python source; tests may name Workspace strings to assert absence."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            modules = [node.module or ''] + [alias.name for alias in node.names]
        elif isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        else:
            modules = []
        for module in modules:
            if set(module.split('.')) & WORKSPACE_MODULES: found.append('imports ' + module)
            if runtime and module.split('.')[0] == 'tools': found.append('runtime imports tools: ' + module)
        names = []
        if isinstance(node, ast.Name): names.append(node.id)
        elif isinstance(node, ast.Attribute): names.append(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): names.append(node.name)
        elif isinstance(node, ast.arg): names.append(node.arg)
        elif isinstance(node, ast.alias): names.append(node.asname or node.name)
        for name in names:
            if name in WORKSPACE_CLASSES: found.append('uses class ' + name)
            if runtime and WORKSPACE_WORDS.search(name): found.append('runtime identifier ' + name)
        if strings and isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in WORKSPACE_TABLES or node.value in WORKSPACE_CLASSES: found.append('names ' + node.value)
            if any(route in node.value for route in WORKSPACE_ROUTES): found.append('route ' + node.value)
    return found

def test_scanner_catches_workspace_references():
    assert violations('from .research_models import ResearchEvent')
    assert violations('import app.permutable')
    assert violations("rows = s.query(Lead).all()")
    assert violations("op.create_table('lead_revision')")
    assert violations("@app.get('/api/leads')\ndef x(): pass")
    assert violations('from tools import seed', runtime=True)
    assert violations('def lead_only_source(): pass', runtime=True)
    assert not violations("headers = {'User-Agent': 'bounded industrial research capture'}", runtime=True)

def test_no_core_file_uses_workspace_code():
    found = {}
    for path in python_files():
        name = str(path.relative_to(ROOT))
        problems = [problem for problem in violations(path.read_text(), strings=path.parts[-2] != 'tests') if (name, problem) not in ALLOWED]
        if problems: found[name] = problems
    assert not found, found

def test_runtime_code_has_no_workspace_features_or_tools():
    found = {str(path.relative_to(ROOT)): problems for path in (ROOT / 'app').rglob('*.py') if (problems := violations(path.read_text(), runtime=True))}
    assert not found, found

def test_no_workspace_module_files():
    present = {path.stem for path in (ROOT / 'app').glob('*.py')} | {path.stem for path in (ROOT / 'tools').glob('*.py')}
    assert not present & WORKSPACE_MODULES

def test_web_screens_have_no_workspace_routes_or_scripts():
    for path in (ROOT / 'app' / 'static').iterdir():
        text = path.read_text()
        assert not [route for route in WORKSPACE_ROUTES if route.removeprefix('/api') in text], path
        assert not [script for script in WORKSPACE_SCRIPTS if script in text], path

def test_running_core_loads_only_core_modules_tables_and_routes(tmp_path):
    # A clean interpreter: importing the runtime pulls in no tools and no Workspace module.
    probe = ('import sys, pkgutil, importlib, app\n'
             'for module in pkgutil.iter_modules(app.__path__): importlib.import_module("app." + module.name)\n'
             'from app.main import create_app\n'
             'print(sorted(name for name in sys.modules if name == "tools" or name.startswith(("tools.", "app."))))')
    # Run outside the repository so neither tools/ nor the working directory can be imported.
    loaded = subprocess.run([sys.executable, '-c', probe], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    assert 'tools' not in loaded and not [name for name in WORKSPACE_MODULES if 'app.' + name in loaded], loaded
    for module in pkgutil.iter_modules(app.__path__): importlib.import_module('app.' + module.name)
    assert not set(Base.metadata.tables) & WORKSPACE_TABLES

def test_api_offers_no_workspace_routes(client):
    paths = client.get('/openapi.json').json()['paths']
    assert not [path for path in paths if path.startswith(WORKSPACE_ROUTES)]
    for route in WORKSPACE_ROUTES: assert client.get(route).status_code == 404, route

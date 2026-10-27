"""Load a vendor delivery into the market data area from a recipe: which file, column and instrument.

A recipe (JSON, kept in tools/curated/) names the source and its licence, the instruments, the files to
read with their import settings, untouched companion files to store as evidence without reading them,
and the series left out with the reason. It holds no data values; the files stay in a private folder.

    python -m tools.market_recipe RECIPE.json --root DELIVERY_DIR [--dry-run] [--actor NAME]

Uses DATABASE_URL and SNAPSHOT_DIR. Repeat runs add nothing: same bytes are the same document, same
settings the same build. Prints a summary with the market data quality.
"""
import argparse
import json
import os
from datetime import date
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import DATABASE_URL, make_engine
from app.market import inspect_market_quality
from app.models import Audit, Source, SourceAccess
from app.schemas import MarketImportIn
from tools import market_import

def ensure_source(s, recipe, actor):
    """The recipe's source, registered on first use with its audited access decision."""
    item = recipe['source']
    source = s.scalar(select(Source).where(Source.name == item['name']))
    if source: return source.id
    source = Source(**{k: item[k] for k in ('name', 'publisher', 'source_type', 'url', 'notes')}, access_status='permitted'); s.add(source); s.flush()
    access = item['access']
    decision = SourceAccess(source_id=source.id, status='permitted', allowed_hosts=[], export_allowed=access['export_allowed'], basis=access['basis'],
                            retention=access['retention'], reviewer=actor)
    s.add(decision); s.flush()
    s.add(Audit(actor=actor, action='access_decision', record_id=decision.id, detail={'type': 'source_access', 'export_allowed': access['export_allowed']}))
    s.commit()
    return source.id

def check(recipe, root):
    """Every file exists and every import's settings are valid, before anything is written."""
    for item in recipe['imports'] + recipe.get('companions', []):
        if not (root / item['file']).is_file(): raise ValueError('Missing file in the delivery: ' + item['file'])
    for item in recipe['imports']: MarketImportIn.model_validate(item['settings'])

def run(recipe, root, actor='market-curator', dry_run=False, storage=None, database_url=None):
    root = Path(root)
    check(recipe, root)
    summary = {'recipe': recipe['name'], 'imports': len(recipe['imports']), 'companions': len(recipe.get('companions', [])),
               'instruments': sorted(i['code'] for i in recipe['instruments']), 'left_out': recipe.get('left_out', [])}
    if dry_run: return summary
    storage, url = storage or os.getenv('SNAPSHOT_DIR', 'data/snapshots'), database_url or DATABASE_URL
    with Session(make_engine(url)) as s:
        source_id = ensure_source(s, recipe, actor)
        created = market_import.ensure_instruments(s, recipe['instruments'], actor); s.commit()
        stored = sum(not market_import.register_file(s, storage, root / item['file'], source_id, item['locator'], item['title'],
                                                     date.fromisoformat(item['published_at']), actor)[1] for item in recipe.get('companions', []))
    totals = {'documents': stored, 'builds': 0, 'observations': 0}
    for item in recipe['imports']:
        result = market_import.run(root / item['file'], source_id, item['locator'], item['title'], item['settings'], (), date.fromisoformat(item['published_at']),
                                   actor, storage, url, with_quality=False)
        totals['documents'] += not result['duplicate_document']
        totals['builds'] += not result['duplicate_build']
        totals['observations'] += 0 if result['duplicate_build'] else result['observations']
    with Session(make_engine(url)) as s: quality = inspect_market_quality(s, storage)
    return {**summary, 'source_id': source_id, 'instruments_created': created, **totals,
            'quality': {'status': quality['status'], 'counts': quality['counts'], 'findings': sorted({(f['code'], f['severity']) for f in quality['findings']})}}

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('recipe', type=Path)
    parser.add_argument('--root', required=True, type=Path, help='the unpacked delivery the recipe refers to')
    parser.add_argument('--dry-run', action='store_true', help='check the files and settings; write nothing')
    parser.add_argument('--actor', default=os.getenv('WRITE_ACTOR', 'market-curator'))
    args = parser.parse_args()
    print(json.dumps(run(json.loads(args.recipe.read_text()), args.root, args.actor, args.dry_run), indent=2, default=list))

if __name__ == '__main__': main()

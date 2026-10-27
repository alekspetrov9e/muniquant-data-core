"""Register a market data file (CSV, XLSX or an LSEG JSON response) as a document and read it into market observations.

The file is stored unchanged under its SHA-256 like any other evidence; the import settings say how
to read it (see docs/MARKET_DATA.md). Instruments named by the settings must be registered first, or
given with --instruments (a JSON list; an existing code must match its registered definition).

    python -m tools.market_import FILE --source-id ID --locator URI --title TITLE --spec SPEC.json
                                  [--instruments INSTRUMENTS.json] [--published-at YYYY-MM-DD] [--actor NAME]

The source and its audited access decision are registered beforehand through the API. Uses
DATABASE_URL and SNAPSHOT_DIR like the server. Prints a JSON summary with the market data quality.
"""
import argparse
import json
import os
import re
from datetime import date
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.acquisition import MAX_BYTES, register_bytes
from app.db import DATABASE_URL, make_engine
from app.market import TSV, XLSX, import_table, inspect_market_quality, register_instrument
from app.models import Audit, Instrument, Run
from app.schemas import InstrumentIn, MarketImportIn
from app.services import record

MEDIA = {'.csv': 'text/csv', '.tsv': TSV, '.xlsx': XLSX, '.json': 'application/json'}

def ensure_instruments(s, definitions, actor):
    """Register missing instruments; an already registered code must have the same definition."""
    created = []
    for item in definitions:
        data = InstrumentIn.model_validate(item)
        existing = s.scalar(select(Instrument).where(Instrument.code == data.code))
        if existing:
            current = {key: value for key, value in record(existing).items() if key not in ('id', 'created_at')}
            if current != data.model_dump(): raise ValueError(f'{data.code} is registered with a different definition')
            continue
        obj = register_instrument(s, data)
        s.add(Audit(actor=actor, action='create', record_id=obj.id, detail={'type': 'market_instrument'}))
        created.append(data.code)
    return created

def register_file(s, storage, path, source_id, locator, title, published_at=None, actor='market-curator'):
    """Store a local file unchanged as a document version of the source; the same bytes again are a duplicate."""
    path = Path(path)
    media = MEDIA.get(path.suffix.lower())
    if not media: raise ValueError('Market files are .csv, .tsv, .xlsx or .json (LSEG responses)')
    if not re.fullmatch(r'[a-z][a-z0-9+.-]*:\S+', locator): raise ValueError('The locator is a URI naming where the file came from, e.g. https://... or vendor:...')
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_BYTES: raise ValueError('File is empty or larger than 10 MB')
    doc, duplicate = register_bytes(s, storage, {'source_id': source_id, 'title': title, 'original_url': locator,
                                                 'published_at': published_at.isoformat() if published_at else None, 'media_type': media}, raw)
    s.add(Run(status='duplicate' if duplicate else 'success', pipeline_version='1.0.0',
              manifest={'content_hash': doc.content_hash, 'document_id': doc.id, 'adapter': 'file-v1', 'file_name': path.name}))
    s.add(Audit(actor=actor, action='duplicate' if duplicate else 'acquire', record_id=doc.id, detail={'type': 'documents'}))
    s.commit()
    return doc, duplicate

def run(path, source_id, locator, title, spec, instruments=(), published_at=None, actor='market-curator', storage=None, database_url=None, with_quality=True):
    settings = MarketImportIn.model_validate(spec)
    storage = storage or os.getenv('SNAPSHOT_DIR', 'data/snapshots')
    with Session(make_engine(database_url or DATABASE_URL)) as s:
        created = ensure_instruments(s, instruments, actor)
        doc, duplicate = register_file(s, storage, path, source_id, locator, title, published_at, actor)
        build, repeated = import_table(s, storage, doc.id, settings, actor)
        s.commit()
        quality = inspect_market_quality(s, storage) if with_quality else None
        return {'document_id': doc.id, 'document_version': doc.version, 'content_hash': doc.content_hash, 'duplicate_document': duplicate,
                'instruments_created': created, 'build_id': build.id, 'duplicate_build': repeated, 'observations': len(build.logical_output),
                'quality': quality and {'status': quality['status'], 'counts': quality['counts'],
                                        'findings': [{k: f[k] for k in ('code', 'severity', 'record_id', 'message', 'count') if k in f} for f in quality['findings']]}}

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('file', type=Path)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--locator', required=True, help='URI naming where the file came from')
    parser.add_argument('--title', required=True)
    parser.add_argument('--spec', required=True, type=Path, help='JSON import settings')
    parser.add_argument('--instruments', type=Path, help='JSON list of instrument definitions to register if missing')
    parser.add_argument('--published-at', type=date.fromisoformat)
    parser.add_argument('--actor', default=os.getenv('WRITE_ACTOR', 'market-curator'))
    args = parser.parse_args()
    instruments = json.loads(args.instruments.read_text()) if args.instruments else []
    print(json.dumps(run(args.file, args.source_id, args.locator, args.title, json.loads(args.spec.read_text()), instruments,
                         args.published_at, args.actor), indent=2))

if __name__ == '__main__': main()

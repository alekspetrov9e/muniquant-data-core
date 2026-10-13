"""Demo and migration utility for the old 0.1.0-draft package. NOT the evidence contract.

Freezes, verifies and restores draft bundles (stored outputs, no document re-extraction).
CommodityEvidencePackage 1.0.0 (`python -m app.evidence_cli`) is the only Data Core export.
This tool is outside the runtime package: the Data Core runs without it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile
from sqlalchemy import select
from sqlalchemy.orm import Session
from jsonschema import validate
from app.db import make_engine, DATABASE_URL
from app.models import Entity, Source, Document, Observation, Relationship
from app.services import record, lead_only_source

PIPELINE_VERSION='0.1.0'
SCHEMA=Path(__file__).parent/'package.schema.json'
# The draft format always carried an empty market list; market data is not part of the Data Core.
MODELS={'entities':Entity,'sources':Source,'documents':Document,'observations':Observation,'relationships':Relationship}

def export_package(session, storage):
    # Lead-only documents (licensed event feeds) are curator work items, never package evidence.
    lead_sources = {src.id for src in session.scalars(select(Source)) if lead_only_source(session,src.id)}
    docs = {d.id:record(d) for d in session.scalars(select(Document)).all() if d.source_id not in lead_sources}
    for doc in docs.values():
        path=Path(storage)/doc['content_hash']
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=doc['content_hash']:
            raise ValueError('Evidence snapshot missing or corrupted: '+doc['id'])
        doc['evidence_url']='/api/documents/'+doc['id']+'/content'
    package={'package_version':'0.1.0-draft','pipeline_version':PIPELINE_VERSION,
             'entities': [record(e) for e in session.scalars(select(Entity).order_by(Entity.id))],
             'sources': [record(s) for s in session.scalars(select(Source).order_by(Source.id)) if s.id not in lead_sources],
             'documents':sorted(docs.values(),key=lambda d:d['id']),
             'observations': [dict(record(o),resolution_status='resolved') for o in session.scalars(select(Observation).order_by(Observation.id))],
             'relationships':[record(r) for r in session.scalars(select(Relationship).order_by(Relationship.id))],
             'market_observations':[]}
    logical=json.dumps(package, sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    package['build_hash']=hashlib.sha256(logical).hexdigest()
    return package

def freeze(session, storage, target):
    package=export_package(session,storage)
    validate(package,json.loads(SCHEMA.read_text()))
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('package.json',json.dumps(package,sort_keys=True,indent=2))
        for digest in sorted({d['content_hash'] for d in package['documents']}):
            archive.write(Path(storage)/digest,'snapshots/'+digest)
    return package['build_hash']

def load_verified(bundle):
    with zipfile.ZipFile(bundle) as archive:
        if sum(i.file_size for i in archive.infolist())>100_000_000:
            raise ValueError('Bundle exceeds 100 MB uncompressed limit')
        package=json.loads(archive.read('package.json'))
        validate(package,json.loads(SCHEMA.read_text()))
        content={k:v for k,v in package.items() if k!='build_hash'}
        digest=hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        if digest!=package['build_hash']: raise ValueError('Package hash mismatch')
        snapshots={}
        for doc in package['documents']:
            raw=archive.read('snapshots/'+doc['content_hash'])
            if hashlib.sha256(raw).hexdigest()!=doc['content_hash']: raise ValueError('Snapshot hash mismatch')
            snapshots[doc['content_hash']]=raw
        return package,snapshots

def restore(session, storage, bundle):
    package,snapshots=load_verified(bundle)
    if package['market_observations']: raise ValueError('Market observations are not part of the Data Core')
    if any(session.scalar(select(model.id).limit(1)) for model in MODELS.values()):
        raise ValueError('Restore requires an empty migrated database')
    # Select named archive entries; never extract archive-controlled paths.
    Path(storage).mkdir(parents=True,exist_ok=True)
    for digest,raw in snapshots.items():
        path=Path(storage)/digest
        if path.exists() and path.read_bytes()!=raw: raise ValueError('Conflicting snapshot on disk')
        path.write_bytes(raw)
    try:
        for key,model in MODELS.items():
            columns={c.name for c in model.__table__.columns}
            for item in package[key]: session.add(model(**{k:v for k,v in item.items() if k in columns}))
            session.flush()
        reproduced=export_package(session,storage)
        if reproduced!=package: raise ValueError('Restored package does not match bundle')
        session.commit()
    except Exception:
        session.rollback(); raise
    return package['build_hash']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['freeze','verify','restore'])
    parser.add_argument('path')
    args=parser.parse_args()
    storage=os.getenv('SNAPSHOT_DIR','data/snapshots')
    if args.operation=='verify': print(load_verified(args.path)[0]['build_hash']); return
    with Session(make_engine(DATABASE_URL)) as session:
        print((freeze if args.operation=='freeze' else restore)(session,storage,args.path))
if __name__=='__main__': main()

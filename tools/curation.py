"""Load a curated set of official sources into the Core: explicit URLs, verified identities and facts.

A curation file (JSON) lists sources with their exact hosts, documents (URLs), plants and companies,
owner and operator links, capacity extractions and statuses. Every name, link and status must appear
verbatim in the captured text of its document; capacities go through the Core's own versioned
extractor and matching. Nothing is inferred: a snippet that is no longer on the page stops the run.

    python -m tools.curation FILE --online --as-of YYYY-MM-DD --output DIR [--skip-source KEY] [--recapture]

Run it on a database that already holds the pilot (tools.pilot) to grow the same dataset; existing
plants are found by the same stable IDs. The output directory receives the evidence package, a frozen
bundle with its replay result and a summary. Captured pages stay local (data/ is not in git).
"""
import argparse
import json
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.acquisition import acquire_remote, fetch_once
from app.contract import export_v1, freeze_v1, replay_v1
from app.db import DATABASE_URL, make_engine
from app.domain import add_alias, sync_entity
from app.models import (Audit, CompanyFacilityRelationship, Document, Entity, EntityEvidence, Observation, Relationship, Source, SourceAccess)
from app.pipeline import extract
from app.schemas import ExtractionIn, ObservationIn, RetrievalIn
from app.services import add_observation
from tools.pilot import identifier, text_for

ACTOR = 'authorized-pilot-curator'
STATUSES = ('operating', 'closed', 'suspended', 'planned', 'construction')

def present(snippet, text, what):
    if not snippet or ' '.join(snippet.split()).casefold() not in ' '.join(text.split()).casefold():
        raise ValueError(f'{what}: {snippet!r} is not in the captured document')

def without_sources(curation, keys):
    """The curation minus the given sources and everything that depends on their documents."""
    keys = set(keys)
    unknown = keys - {item['key'] for item in curation['sources']}
    if unknown: raise ValueError('Unknown sources: ' + ', '.join(sorted(unknown)))
    docs = {item['key'] for item in curation['documents'] if item['source'] in keys}
    facilities = {item['name'] for item in curation['facilities'] if item['document'] in docs}
    companies = {item['name'] for item in curation['companies'] if item['document'] in docs}
    kept = {**curation, 'sources': [i for i in curation['sources'] if i['key'] not in keys],
            'documents': [i for i in curation['documents'] if i['key'] not in docs],
            'facilities': [{**i, 'aliases': [a for a in i.get('aliases', []) if not isinstance(a, dict) or a['document'] not in docs]}
                           for i in curation['facilities'] if i['name'] not in facilities],
            'companies': [i for i in curation['companies'] if i['name'] not in companies],
            'relationships': [i for i in curation['relationships'] if i['document'] not in docs and i['company'] not in companies and i['facility'] not in facilities],
            'capacities': [i for i in curation['capacities'] if i['document'] not in docs and i.get('facility') not in facilities],
            'statuses': [i for i in curation['statuses'] if i['document'] not in docs and i['facility'] not in facilities]}
    skipped = {name: len(curation[name]) - len(kept[name]) for name in ('sources', 'documents', 'facilities', 'companies', 'relationships', 'capacities', 'statuses')}
    return kept, skipped

def load(s, storage, curation, as_of, fetch=fetch_once, recapture=False):
    """Capture and register everything in the curation; repeat runs add nothing new.

    A URL already captured for its source is reused (its latest version) unless recapture is set:
    many pages differ in a few bytes on every request, and each capture would be a new version."""
    counts = dict.fromkeys(('sources', 'documents', 'facilities', 'companies', 'relationships', 'capacities', 'statuses'), 0)
    for item in curation['sources']:
        sid = identifier('source:' + item['key'])
        if not s.get(Source, sid):
            s.add(Source(id=sid, name=item['publisher'] + ' public industrial publications', publisher=item['publisher'], source_type=item['source_type'],
                         url=item['url'], access_status='permitted', notes='Public official publication for local research. No third-party redistribution license asserted.'))
            s.flush(); counts['sources'] += 1
        if not s.scalar(select(SourceAccess).where(SourceAccess.source_id == sid)):
            hosts = sorted(set(item.get('hosts') or [urlsplit(item['url']).hostname]))
            s.add(SourceAccess(source_id=sid, status='permitted', allowed_hosts=hosts, reviewer=ACTOR,
                               basis='Curator-approved bounded capture of publicly published official industrial material for the DC2 pilot',
                               retention='Local evidence retention only; review publisher terms before redistribution or shared hosting'))
    s.commit()
    docs, texts = {}, {}
    for item in curation['documents']:
        data = RetrievalIn(source_id=identifier('source:' + item['source']), url=item['url'], title=item['title'], published_at=item.get('published_at'))
        doc = None if recapture else s.scalar(select(Document).where(Document.source_id == data.source_id, Document.original_url == data.url).order_by(Document.version.desc()))
        duplicate = doc is not None
        if not doc: doc, duplicate, _ = acquire_remote(s, storage, data, ACTOR, fetch=fetch)
        docs[item['key']], texts[item['key']] = doc, text_for(doc, storage)
        counts['documents'] += not duplicate
    def entity(kind, item):
        eid = identifier(f"{kind}:{item['name']}")
        found = s.get(Entity, eid)
        if found: return found, False
        found = Entity(id=eid, name=item['name'], kind=kind, country=item['country'], region=item.get('region', ''),
                       facility_type=item.get('facility_type'), commodity=item.get('commodity', 'aluminium'), aliases=[])
        s.add(found); s.flush(); sync_entity(s, found, ACTOR)
        return found, True
    facilities = {}
    for item in curation['facilities']:
        present(item['identity_snippet'], texts[item['document']], item['name'])
        facility, created = entity('facility', item)
        facilities[item['name']] = facility; counts['facilities'] += created
        if not s.get(EntityEvidence, (facility.id, docs[item['document']].id)):
            s.add(EntityEvidence(entity_id=facility.id, document_id=docs[item['document']].id, evidence_reference='Official text: ' + item['identity_snippet'], reviewer=ACTOR,
                                 reason='Curated plant name, country and industrial class from an official publication; no market inference'))
        for alias in item.get('aliases', []):
            # An alias names the document that writes it; a bare string may come from any captured document.
            name, named = (alias['name'], [alias['document']]) if isinstance(alias, dict) else (alias, [item['document'], *docs])
            # A whole-word match, so a short alias such as ABI is not found inside another word.
            pattern = re.compile(r'(?<!\w)' + re.escape(' '.join(name.split())) + r'(?!\w)', re.IGNORECASE)
            document = next((key for key in named if pattern.search(' '.join(texts[key].split()))), None)
            if not document: raise ValueError(f"{item['name']}: alias {name!r} is not in {'its document' if isinstance(alias, dict) else 'any captured document'}")
            add_alias(s, facility.id, name, ACTOR, f'Name as written in {docs[document].title}')
    companies = {}
    for item in curation['companies']:
        present(item['snippet'], texts[item['document']], item['name'])
        company, created = entity('company', item)
        companies[item['name']] = company; counts['companies'] += created
        if not s.get(EntityEvidence, (company.id, docs[item['document']].id)):
            s.add(EntityEvidence(entity_id=company.id, document_id=docs[item['document']].id, evidence_reference='Official text: ' + item['snippet'], reviewer=ACTOR,
                                 reason='Company name as written in an official publication; country: ' + item.get('country_basis', 'as stated in the source')))
    s.commit()
    for item in curation['relationships']:
        present(item['snippet'], texts[item['document']], f"{item['company']} {item['role']} {item['facility']}")
        doc = docs[item['document']]
        valid_from = date.fromisoformat(item.get('valid_from') or doc.published_at or as_of)
        rid = identifier(f"relationship:{item['company']}:{item['role']}:{item['facility']}:{doc.id}")
        if s.get(Relationship, rid): continue
        company, facility = companies[item['company']], facilities[item['facility']]
        share = Decimal(str(item['percentage'])) if item.get('percentage') is not None else None
        valid_to = date.fromisoformat(item['valid_to']) if item.get('valid_to') else None
        s.add(Relationship(id=rid, company_id=company.id, facility_id=facility.id, role=item['role'], percentage=float(share) if share is not None else None,
                           valid_from=valid_from.isoformat(), valid_to=valid_to.isoformat() if valid_to else None, document_id=doc.id)); s.flush()
        s.add(CompanyFacilityRelationship(relationship_id=rid, company_id=company.id, facility_id=facility.id, document_id=doc.id, role=item['role'],
                                          percentage=share, valid_from=valid_from, valid_to=valid_to, evidence_reference='Official text: ' + item['snippet']))
        s.add(Audit(actor=ACTOR, action='curated_relationship', record_id=rid, detail={'document': item['document'], 'as_of_policy': 'publication date, else capture date'}))
        counts['relationships'] += 1
    s.commit()
    for item in curation['capacities']:
        doc = docs[item['document']]
        spec = {**item['spec'], 'valid_from': item['spec'].get('valid_from') or doc.published_at or as_of}
        _, duplicate = extract(s, storage, doc.id, ExtractionIn(**spec), ACTOR); s.commit()
        counts['capacities'] += not duplicate
    for item in curation['statuses']:
        if item['status'] not in STATUSES: raise ValueError(f"{item['facility']}: unknown status {item['status']}")
        present(item['snippet'], texts[item['document']], f"{item['facility']} {item['status']}")
        doc, facility = docs[item['document']], facilities[item['facility']]
        valid_from = item.get('valid_from') or doc.published_at or as_of
        reference = 'Official text: ' + item['snippet']
        if s.scalar(select(Observation).where(Observation.entity_id == facility.id, Observation.document_id == doc.id, Observation.attribute == 'status', Observation.evidence_reference == reference)): continue
        obs = add_observation(s, ObservationIn(entity_id=facility.id, document_id=doc.id, attribute='status', reported_value=item['status'], reported_unit='status',
                                               valid_from=valid_from, valid_to=item.get('valid_to'), evidence_reference=reference))
        s.add(Audit(actor=ACTOR, action='curated_status', record_id=obs.id, detail={'document': item['document']}))
        counts['statuses'] += 1
    s.commit()
    return counts

def run(s, storage, curation, as_of, output, fetch=fetch_once, recapture=False):
    counts = load(s, storage, curation, as_of, fetch, recapture)
    package = export_v1(s, storage)
    root = Path(output); root.mkdir(parents=True, exist_ok=True)
    bundle = root / 'frozen-evidence.zip'
    if bundle.exists(): raise ValueError('Output bundle already exists; choose a new output directory')
    (root / 'evidence-package.json').write_text(json.dumps(package, indent=2))
    freeze_v1(s, storage, bundle)
    facilities = [e for e in package['entities'] if e['entity_type'] == 'facility']
    summary = {'as_of': as_of, 'added': counts, 'facilities': len(facilities), 'companies': len(package['entities']) - len(facilities),
               'countries': sorted({e['country'] for e in facilities}), 'source_families': len(package['sources']), 'documents': len(package['documents']),
               'records': len(package['records']), 'relationships': len(package['relationships']), 'build_hash': package['build_hash'],
               'replay': replay_v1(bundle)}
    (root / 'validation.json').write_text(json.dumps(summary, indent=2))
    return summary

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('file', type=Path)
    parser.add_argument('--online', action='store_true', help='explicitly approve the bounded captures listed in the file')
    parser.add_argument('--as-of', required=True, type=date.fromisoformat)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--skip-source', action='append', default=[], help='leave out a source and everything that depends on its documents')
    parser.add_argument('--recapture', action='store_true', help='fetch every URL again instead of reusing pages already captured')
    args = parser.parse_args()
    if not args.online: parser.error('Use --online to approve these explicit public-source captures; use evidence_cli replay for offline rebuilds')
    curation, skipped = without_sources(json.loads(args.file.read_text()), args.skip_source)
    with Session(make_engine(DATABASE_URL)) as s:
        summary = run(s, os.getenv('SNAPSHOT_DIR', 'data/snapshots'), curation, args.as_of.isoformat(), args.output, recapture=args.recapture)
    print(json.dumps({**summary, 'skipped': skipped}, indent=2))

if __name__ == '__main__': main()

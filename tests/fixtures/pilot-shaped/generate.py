"""Generate the pilot-shaped legacy fixture with the 10 October 2026 pilot code (commit c6d0411).

Synthetic, fictional content only. This script is provenance for the committed fixture; it runs
against a checkout of c6d0411, not against the Data Core (see README.md in this folder).
It follows app.pilot: audited permitted sources, bounded captures (served offline here), curated
identities with identity evidence, versioned HTML/PDF/CSV extraction, sourced ownership and
operator relationships, then export, freeze and replay. It adds what the real pilot lacked:
an ambiguous name accepted by review, an unknown name rejected by review and a manual fact.
"""
import argparse, io, json, os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL
from urllib.parse import urlsplit
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db import make_engine, DATABASE_URL
from app.models import Entity, Source, SourceAccess, EntityEvidence, Relationship, CompanyFacilityRelationship, Audit, Candidate
from app.domain import sync_entity
from app.acquisition import acquire_remote
from app.pipeline import extract
from app.schemas import RetrievalIn, ExtractionIn
from app.contract import export_v1, freeze_v1, replay_v1
from app.main import create_app
from sqlalchemy import select

ACTOR = 'fixture-pilot-curator'
MARK = 'SYNTHETIC TEST FIXTURE - fictional plants and companies, not industrial facts.'
SOURCES = {'northern': ('Example Northern Aluminium', 'https://example.org/northern/'),
           'southern': ('Example Southern Smelting', 'https://example.com/southern/')}

def html(body):
    return f'<html><head><title>Fixture</title><script>var ignored = 1;</script></head><body><h1>{MARK}</h1>{body}</body></html>'.encode()

def pdf():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    for lines in [[MARK, 'SOUTH BAY SMELTER fact sheet', 'South Bay Smelter has an annual nameplate production capacity of 358,000 metric tons.',
                   'Ownership: Example Southern Smelting 55%, Example Partner Holdings 22.5%, Example Metals Investment 22.5%.',
                   'Operations: day-to-day operation by Example Southern Smelting.'],
                  [MARK, 'HARBOUR POINT header printed on the wrong page', 'annual nameplate production capacity of 999,999 metric tons']]:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        text = ''.join(f'BT /F1 10 Tf 40 {740 - 20 * index} Td ({line}) Tj ET\n' for index, line in enumerate(lines))
        stream.set_data(text.encode('latin-1'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    out = io.BytesIO(); writer.write(out); return out.getvalue()

# Every row's locator carries the synthetic marker; the CSV adapter reads every line as data.
CSV = ('facility_name,country,reported_value,reported_unit,valid_from,valid_to,attribute,evidence_reference\n'
       'East Ridge Refinery,AU,1.4,Mt/year,2025-01-01,,capacity,synthetic test fixture register row East Ridge Refinery\n'
       'Ridge Operations,AU,9.5,Mt/year,2025-01-01,,capacity,synthetic test fixture register row Ridge Operations\n'
       'Unknown Lagoon Works,NZ,300,kt/year,2025-01-01,,capacity,synthetic test fixture register row Unknown Lagoon Works\n').encode()

# Each URL serves its versions in order, so a second capture of a revised page creates version 2.
PAGES = {
    'https://example.org/northern/news/fjord-capacity.html': [
        html('<p>North Fjord Works has an annual production capacity of 197,000 tonnes of primary aluminium.</p>'),
        html('<p>North Fjord Works has an annual production capacity of 205,000 tonnes of primary aluminium after the 2025 upgrade.</p>')],
    'https://example.org/northern/operations.html': [
        html('<p>Operations: North Fjord Works (Norway) and Harbour Point (Norway) are operating smelters. '
             'East Ridge refinery and West Ridge bauxite mine form the Ridge Operations in Australia.</p>')],
    'https://example.com/southern/bay-fact-sheet.pdf': [pdf()],
    'https://example.com/southern/register.csv': [CSV]}
MEDIA = {'.html': 'text/html', '.pdf': 'application/pdf', '.csv': 'text/csv'}
served = {}

def fetch(url, allowed_hosts):
    if urlsplit(url).hostname not in allowed_hosts: raise ValueError('Host not approved in source-access policy')
    index = served.get(url, 0); served[url] = index + 1
    return 200, PAGES[url][min(index, len(PAGES[url]) - 1)], MEDIA[Path(urlsplit(url).path).suffix], url

ASSETS = [('North Fjord Works', 'NO', 'smelter', 'aluminium', 'fjord-v1', 'North Fjord Works', []),
          ('Harbour Point Smelter', 'NO', 'smelter', 'aluminium', 'operations', 'Harbour Point', ['Harbour Point']),
          ('South Bay Smelter', 'AU', 'smelter', 'aluminium', 'bay', 'SOUTH BAY SMELTER', []),
          ('East Ridge Refinery', 'AU', 'refinery', 'alumina', 'operations', 'East Ridge', ['East Ridge', 'Ridge Operations']),
          ('West Ridge Mine', 'AU', 'bauxite_mine', 'bauxite', 'operations', 'West Ridge', ['West Ridge', 'Ridge Operations'])]
COMPANIES = [('Example Northern Aluminium', 'NO'), ('Example Southern Smelting', 'AU'), ('Example Partner Holdings', 'GB'), ('Example Metals Investment', 'CN')]

def identifier(label): return str(uuid5(NAMESPACE_URL, 'muniquant-fixture:' + label))

def populate(s, storage, output, as_of):
    for key, (publisher, url) in SOURCES.items():
        sid = identifier('source:' + key)
        s.add(Source(id=sid, name=publisher + ' public industrial publications', publisher=publisher, source_type='company', url=url, access_status='permitted',
                     notes='Fictional fixture publisher for software tests. ' + MARK)); s.flush()
        s.add(SourceAccess(source_id=sid, status='permitted', allowed_hosts=[urlsplit(url).hostname], basis='Fixture capture policy for software tests of the pilot pipeline',
                           retention='Fixture only; fictional content', reviewer=ACTOR))
    s.commit()
    docs = {}
    for key, source_key, url, published in [('fjord-v1', 'northern', 'https://example.org/northern/news/fjord-capacity.html', '2024-12-19'),
                                            ('operations', 'northern', 'https://example.org/northern/operations.html', None),
                                            ('bay', 'southern', 'https://example.com/southern/bay-fact-sheet.pdf', None),
                                            ('register', 'southern', 'https://example.com/southern/register.csv', '2025-03-31'),
                                            ('fjord-v2', 'northern', 'https://example.org/northern/news/fjord-capacity.html', '2025-06-30')]:
        doc, _, _ = acquire_remote(s, storage, RetrievalIn(source_id=identifier('source:' + source_key), url=url, title=key + ' fixture evidence', published_at=published), ACTOR, fetch)
        docs[key] = doc
    assets = {}
    for name, country, kind, commodity, doc_key, needle, aliases in ASSETS:
        entity = Entity(id=identifier('facility:' + name), name=name, kind='facility', country=country, facility_type=kind, commodity=commodity, region='', aliases=aliases)
        s.add(entity); s.flush(); sync_entity(s, entity, ACTOR)
        s.add(EntityEvidence(entity_id=entity.id, document_id=docs[doc_key].id, evidence_reference=('PDF page 1: ' if doc_key == 'bay' else 'Fixture operations text: ') + needle,
                             reviewer=ACTOR, reason='Curated fixture facility name, country and industrial class from the fixture source'))
        assets[name] = entity
    companies = {}
    for name, country in COMPANIES:
        company = Entity(id=identifier('company:' + name), name=name, kind='company', country=country, region='', commodity='aluminium', aliases=[])
        s.add(company); s.flush(); sync_entity(s, company, ACTOR); companies[name] = company
    s.commit()
    capacity = {'facility_name': 'North Fjord Works', 'country': 'NO', 'unit': 't/year', 'prefix': 'annual production capacity of', 'suffix': 'tonnes of primary aluminium'}
    for key, spec in [('fjord-v1', {'adapter': 'html-v1', 'valid_from': '2024-12-19', **capacity}),
                      ('fjord-v2', {'adapter': 'html-v1', 'valid_from': '2025-06-30', **capacity}),
                      ('bay', {'adapter': 'pdf-v1', 'facility_name': 'South Bay Smelter', 'country': 'AU', 'valid_from': as_of, 'unit': 't/year',
                               'prefix': 'annual nameplate production capacity of', 'suffix': 'metric tons', 'page': 1}),
                      # Same stable sentinel as POST /api/import/csv: CSV rows carry their own dates.
                      ('register', {'adapter': 'csv-v1', 'valid_from': '1970-01-01'})]:
        extract(s, storage, docs[key].id, ExtractionIn(**spec), ACTOR); s.commit()
    for company_name, role, percentage in [('Example Southern Smelting', 'OWNS', '55'), ('Example Partner Holdings', 'OWNS', '22.5'),
                                           ('Example Metals Investment', 'OWNS', '22.5'), ('Example Southern Smelting', 'OPERATES', None)]:
        rid = identifier('bay:' + company_name + ':' + role)
        s.add(Relationship(id=rid, company_id=companies[company_name].id, facility_id=assets['South Bay Smelter'].id, role=role, percentage=float(percentage) if percentage else None,
                           valid_from=as_of, document_id=docs['bay'].id)); s.flush()
        s.add(CompanyFacilityRelationship(relationship_id=rid, company_id=companies[company_name].id, facility_id=assets['South Bay Smelter'].id, document_id=docs['bay'].id,
                                          role=role, percentage=Decimal(percentage) if percentage else None, valid_from=date.fromisoformat(as_of),
                                          evidence_reference='PDF page 1, Ownership and Operations lines'))
        s.add(Audit(actor=ACTOR, action='curated_relationship', record_id=rid, detail={'source': 'Fixture fact sheet page 1', 'as_of_policy': 'snapshot observation date, not historical change date'}))
    s.commit()
    return {key: doc.id for key, doc in docs.items()}, {name: entity.id for name, entity in assets.items()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True); parser.add_argument('--as-of', default='2026-10-10')
    args = parser.parse_args()
    storage = os.getenv('SNAPSHOT_DIR', 'data/snapshots')
    with Session(make_engine(DATABASE_URL)) as s:
        docs, assets = populate(s, storage, args.output, args.as_of)
        reviews = {c.raw_name: c.review_id for c in s.scalars(select(Candidate).where(Candidate.review_id.is_not(None)))}
    # Human decisions and a manual fact go through the pilot-era API, as a curator would record them.
    app = create_app(DATABASE_URL, storage, write_token='fixture-token')
    with TestClient(app) as client:
        client.headers['Authorization'] = 'Bearer fixture-token'
        for raw_name, selected, reason in [('Ridge Operations', assets['West Ridge Mine'], 'Register row heading names the bauxite operation of the Ridge pair'),
                                           ('Unknown Lagoon Works', None, 'No registered facility matches this fixture name')]:
            response = client.post('/api/reviews/' + reviews[raw_name] + '/decision', json={'selected_entity_id': selected, 'reason': reason})
            assert response.status_code == 200, response.text
        response = client.post('/api/observations', json={'entity_id': assets['North Fjord Works'], 'document_id': docs['operations'], 'attribute': 'status',
                                                          'reported_value': 'operating', 'reported_unit': 'status', 'valid_from': args.as_of,
                                                          'evidence_reference': 'Fixture operations text: North Fjord Works operating'})
        assert response.status_code == 201, response.text
    app.state.engine.dispose()
    with Session(make_engine(DATABASE_URL)) as s:
        package = export_v1(s, storage)
        root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
        (root / 'pilot-evidence-package.json').write_text(json.dumps(package, indent=2))
        bundle = root / 'pilot-frozen-evidence.zip'
        freeze_v1(s, storage, bundle)
        replay = replay_v1(bundle)
        sources = s.scalars(select(Source)).all()
        summary = {'as_of': args.as_of, 'facilities': len(ASSETS), 'company_records': len(COMPANIES), 'source_families': len(SOURCES),
                   'source_urls': len(PAGES), 'registered_documents': len(package['documents']), 'parsed_capacity_observations': len(package['records']),
                   'relationships': len(package['relationships']), 'build_hash': package['build_hash'], 'replay': replay,
                   'limitations': ['Synthetic fixture generated by the 10 October 2026 pilot code; not industrial data']}
        assert len(sources) == len(SOURCES)
        (root / 'pilot-validation.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

if __name__ == '__main__': main()

"""tools/curation.py: curated official sources are captured, verified against their text and replayable.

The pages are synthetic and served by a stand-in for the network."""
import json
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import Entity, Observation, Relationship
from tools import curation

PAGE = ('<html><body><h1>Synthetic Metals operations</h1><p>The Fjordvik Smelter (also known as Fjordvik Works) in Norway '
        'has an annual production capacity of 210,000 tonnes of primary aluminium. Synthetic Metals ASA owns 60% and '
        'Example Partners owns 40%; Synthetic Metals ASA operates the plant.</p><p>The Bayside Refinery was closed in 2024.</p></body></html>')
CURATION = {
    'sources': [{'key': 'synthetic-metals', 'publisher': 'Synthetic Metals', 'source_type': 'company', 'url': 'https://example.org/', 'hosts': ['example.org']}],
    'documents': [{'key': 'ops', 'source': 'synthetic-metals', 'url': 'https://example.org/operations', 'title': 'Synthetic operations page', 'published_at': '2025-03-01'}],
    'facilities': [{'name': 'Fjordvik Smelter', 'aliases': ['Fjordvik Works'], 'country': 'NO', 'facility_type': 'smelter', 'commodity': 'aluminium', 'document': 'ops', 'identity_snippet': 'The Fjordvik Smelter'},
                   {'name': 'Bayside Refinery', 'country': 'NO', 'facility_type': 'refinery', 'commodity': 'alumina', 'document': 'ops', 'identity_snippet': 'The Bayside Refinery'}],
    'companies': [{'name': 'Synthetic Metals ASA', 'country': 'NO', 'document': 'ops', 'snippet': 'Synthetic Metals ASA owns 60%'},
                  {'name': 'Example Partners', 'country': 'NO', 'document': 'ops', 'snippet': 'Example Partners owns 40%'}],
    'relationships': [{'company': 'Synthetic Metals ASA', 'facility': 'Fjordvik Smelter', 'role': 'OWNS', 'percentage': 60, 'document': 'ops', 'snippet': 'Synthetic Metals ASA owns 60%'},
                      {'company': 'Example Partners', 'facility': 'Fjordvik Smelter', 'role': 'OWNS', 'percentage': 40, 'document': 'ops', 'snippet': 'Example Partners owns 40%'},
                      {'company': 'Synthetic Metals ASA', 'facility': 'Fjordvik Smelter', 'role': 'OPERATES', 'document': 'ops', 'snippet': 'Synthetic Metals ASA operates the plant'}],
    'capacities': [{'document': 'ops', 'spec': {'adapter': 'html-v1', 'facility_name': 'Fjordvik Works', 'country': 'NO', 'unit': 't/year', 'attribute': 'capacity',
                                                 'prefix': 'annual production capacity of', 'suffix': 'tonnes of primary aluminium'}}],
    'statuses': [{'facility': 'Bayside Refinery', 'status': 'closed', 'document': 'ops', 'snippet': 'The Bayside Refinery was closed in 2024', 'valid_from': '2024-01-01'}]}

def fetch(page=PAGE):
    def serve(url, hosts, headers=None):
        assert 'example.org' in hosts
        return 200, page.encode(), 'text/html', url
    return serve

def test_curated_sources_become_traceable_plants_links_and_facts(client, tmp_path):
    storage = client.app.state.storage
    with Session(client.app.state.engine) as s:
        summary = curation.run(s, storage, CURATION, '2026-10-27', tmp_path / 'out', fetch())
        assert summary['added'] == {'sources': 1, 'documents': 1, 'facilities': 2, 'companies': 2, 'relationships': 3, 'capacities': 1, 'statuses': 1}
        assert summary['replay']['equivalent'] and summary['facilities'] == 2
        fjordvik = s.scalar(select(Entity).where(Entity.name == 'Fjordvik Smelter'))
        assert fjordvik.aliases == ['Fjordvik Works']
        capacity = s.scalar(select(Observation).where(Observation.entity_id == fjordvik.id, Observation.attribute == 'capacity'))
        assert (capacity.reported_value, capacity.valid_from) == ('210,000', '2025-03-01')
        assert s.scalar(select(func.count()).select_from(Relationship)) == 3
        def offline(url, hosts, headers=None): raise AssertionError('captured pages are reused')
        again = curation.load(s, storage, CURATION, '2026-10-27', offline)
        assert again == dict.fromkeys(again, 0)
        changed = curation.load(s, storage, CURATION, '2026-10-27', fetch(PAGE.replace('</body>', '<!-- synthetic nonce --></body>')), recapture=True)
        assert changed['documents'] == 1 and changed['capacities'] == 1  # a recaptured page is a new version with its own extraction
    package = json.loads((tmp_path / 'out' / 'evidence-package.json').read_text())
    status = next(r for r in package['records'] if r['attribute_type'] == 'status')
    assert status['reported_value'] == 'closed' and status['evidence_reference'] == 'Official text: The Bayside Refinery was closed in 2024'

@pytest.mark.parametrize('changed', ['Fjordvik Smelter', 'owns 60%', 'was closed in 2024'])
def test_a_snippet_missing_from_the_page_stops_the_run(client, changed):
    with Session(client.app.state.engine) as s, pytest.raises(ValueError, match='not in the captured document'):
        curation.load(s, client.app.state.storage, CURATION, '2026-10-27', fetch(PAGE.replace(changed, 'something else')))

def test_a_source_can_be_left_out_with_everything_that_depends_on_it():
    other = {**CURATION, 'sources': CURATION['sources'] + [{'key': 'filings', 'publisher': 'Regulator', 'source_type': 'regulator', 'url': 'https://example.com/'}],
             'documents': CURATION['documents'] + [{'key': 'filing', 'source': 'filings', 'url': 'https://example.com/f', 'title': 'Filing'}],
             'relationships': CURATION['relationships'] + [{'company': 'Example Partners', 'facility': 'Fjordvik Smelter', 'role': 'OWNS', 'percentage': 40, 'document': 'filing', 'snippet': 'x'}]}
    kept, skipped = curation.without_sources(other, ['filings'])
    assert kept['sources'] == CURATION['sources'] and kept['relationships'] == CURATION['relationships']
    assert skipped == {'sources': 1, 'documents': 1, 'facilities': 0, 'companies': 0, 'relationships': 1, 'capacities': 0, 'statuses': 0}
    with pytest.raises(ValueError, match='Unknown sources'): curation.without_sources(other, ['nope'])

def test_the_capture_client_declares_an_optional_contact(monkeypatch):
    from app.acquisition import user_agent
    assert user_agent() == 'MuniQuantEvidence/1.0 (bounded industrial research capture)'
    monkeypatch.setenv('CAPTURE_CONTACT', 'curator@example.org')
    assert user_agent().endswith('; contact: curator@example.org)')
    monkeypatch.setenv('CAPTURE_CONTACT', 'bad (value)')
    with pytest.raises(ValueError): user_agent()

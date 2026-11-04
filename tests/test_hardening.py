"""Requirement-driven UAT, ambiguity, conflict, load and concurrent-write checks."""
import json
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.models import Entity, EntityAlias, EntitySupersession
from app.domain import add_alias, supersede, sync_entity
from app.services import resolve

def test_fifty_difficult_names_never_trust_ambiguity(client):
    benchmark=json.loads(Path('tests/fixtures/ambiguity-50.json').read_text())
    for entity in benchmark['entities']:
        response=client.post('/api/entities',json=entity)
        assert response.status_code==201,response.text
    with Session(client.app.state.engine) as session:
        for case in benchmark['cases']:
            result=resolve(session,case['raw_name'],case['country'],case['kind'])
            assert result['status']==case['expected_status'],case
            if case['expected_status']=='resolved':
                assert result['candidates'][0]['name']==case['expected_name'],case
            else: assert result['entity_id'] is None,case

def test_a_name_that_grows_under_normalisation_cannot_break_resolve(client):
    expanding='ﷺ'*20  # 20 characters, about 380 after NFKC
    assert client.post('/api/entities',json={'name':expanding,'country':'NO','facility_type':'smelter'}).status_code==422
    plant=client.post('/api/entities',json={'name':'Fjordvik Works','country':'NO','facility_type':'smelter'}).json()
    reason={'reason':'test case'}
    assert client.post(f"/api/entities/{plant['id']}/aliases",json={'name':expanding,**reason}).status_code==422
    # One such name stored before the check must not make every fuzzy search fail
    with Session(client.app.state.engine) as session:
        session.add(Entity(name=expanding,kind='facility',country='NO',facility_type='smelter',commodity='aluminium',region='',aliases=[]))
        session.commit()
    result=client.post('/api/resolve',json={'name':'Fjordvik Work','country':'NO'}).json()
    assert result['status']=='unresolved' and result['candidates'][0]['id']==plant['id']
    assert client.post('/api/resolve',json={'name':expanding,'country':'NO'}).json()['status']=='resolved'

def test_larger_dataset_csv_and_pagination(client,example):
    _,_,_,payload=example
    with Session(client.app.state.engine) as session:
        for index in range(500):
            entity=Entity(name=f'Load Fixture {index:03}',kind='facility',country='NO',facility_type='smelter',commodity='aluminium',region='',aliases=[])
            session.add(entity);session.flush();sync_entity(session,entity,'load-fixture')
        session.commit()
    csv='facility_name,country,reported_value,reported_unit,valid_from,evidence_reference\n'+''.join(f'Load Fixture {index:03},NO,{100+index},kt/year,2025-01-01,synthetic row {index+2}\n' for index in range(500))
    doc=client.post('/api/documents',json={**payload,'original_url':'https://example.org/load','media_type':'text/csv','content':csv}).json()
    imported=client.post('/api/import/csv',json={'document_id':doc['id']})
    assert imported.status_code==200,imported.text
    assert imported.json()['inserted']==500
    page=client.get('/api/records/observations?offset=450&limit=50').json()
    assert page['total']==500 and len(page['records'])==50
    assert len(client.get('/api/export').json()['records'])==500

def test_overlapping_capacity_conflicts_and_historical_status(client,example):
    entity,_,doc,_=example
    base={'entity_id':entity['id'],'document_id':doc['id'],'valid_from':'2025-01-01','valid_to':'2025-12-31','evidence_reference':'synthetic conflict fixture'}
    for value,unit in [('400','kt/year'),('0.4','Mt/year'),('410000','t/year')]:
        assert client.post('/api/observations',json={**base,'reported_value':value,'reported_unit':unit}).status_code==201
    assert client.post('/api/observations',json={**base,'attribute':'status','reported_value':'closed','reported_unit':'status'}).status_code==201
    assert client.post('/api/observations',json={**base,'valid_from':'2026-01-01','valid_to':None,'attribute':'status','reported_value':'operating','reported_unit':'status'}).status_code==201
    findings=client.get('/api/quality').json()['findings']
    assert sum(f['code']=='CONFLICTING_OBSERVATIONS' for f in findings)==2
    assert len(client.get('/api/export').json()['records'])==5
    with client.app.state.engine.begin() as connection:
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            connection.execute(text("UPDATE observations SET reported_unit='MW' WHERE attribute='capacity'"))

def test_failed_parser_manifest_and_new_identity_review(client,example):
    _,_,_,payload=example
    doc=client.post('/api/documents',json={**payload,'content':'no capacity here','media_type':'text/html'}).json()
    spec={'adapter':'html-v1','facility_name':'New Verified Site','country':'AU','valid_from':'2025-01-01','prefix':'capacity','suffix':'tonnes','unit':'t/year'}
    assert client.post('/api/documents/'+doc['id']+'/extract',json=spec).status_code==422
    assert any(r['status']=='failed' and r['manifest'].get('document_id')==doc['id'] for r in client.get('/api/workspace').json()['runs'])
    doc=client.post('/api/documents',json={**payload,'content':'capacity 500 tonnes','media_type':'text/html'}).json()
    candidate=client.post('/api/documents/'+doc['id']+'/extract',json=spec).json()['candidates'][0]
    entity=client.post('/api/entities',json={'name':'New Verified Site','country':'AU','facility_type':'smelter'}).json()
    review='/api/reviews/'+candidate['review_id']
    assert client.post(review+'/candidates',json={'entity_id':entity['id'],'reason':'Registered after checking the original facility source'}).status_code==201
    assert client.post(review+'/decision',json={'selected_entity_id':entity['id'],'reason':'Verified source country and canonical site'}).status_code==200
    assert client.get('/api/export').json()['records'][0]['external_entity_id']==entity['id']

def test_extraction_stays_fast_on_long_digit_runs(client,example):
    _,_,_,payload=example
    doc=client.post('/api/documents',json={**payload,'content':'1'*40_000,'media_type':'text/html'}).json()
    spec={'adapter':'html-v1','facility_name':'Test Works','country':'NO','valid_from':'2025-01-01','prefix':'1','suffix':'kt','unit':'kt/year'}
    started=time.monotonic()
    response=client.post('/api/documents/'+doc['id']+'/extract',json=spec)
    # About 28 s while the number pattern was unbounded
    assert response.status_code==422 and time.monotonic()-started<5

def test_concurrent_import_has_one_build_and_observation(client,example):
    _,_,_,payload=example
    csv='facility_name,country,reported_value,reported_unit,valid_from,evidence_reference\nTest Works,NO,400,kt/year,2025-01-01,row 2\n'
    doc=client.post('/api/documents',json={**payload,'media_type':'text/csv','content':csv}).json()
    def submit(_):
        with TestClient(client.app) as parallel:
            return parallel.post('/api/import/csv',json={'document_id':doc['id']},headers={'Authorization':'Bearer test-token'})
    with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(submit,range(2)))
    assert all(response.status_code in (200,409) for response in responses),[r.text for r in responses]
    assert any(response.status_code==200 for response in responses)
    workspace=client.get('/api/workspace').json()
    assert len(workspace['builds'])==1 and len(workspace['observations'])==1

def test_legacy_data_import_preserves_source_and_exact_reported_fact(client,example,new_database,monkeypatch):
    # The Core has no legacy migration chain: existing databases enter through tools/core_import.py.
    from alembic import command
    from alembic.config import Config
    from app.main import create_app
    from tools.core_import import copy
    entity,_,doc,_=example
    obs=client.post('/api/observations',json={'entity_id':entity['id'],'document_id':doc['id'],'reported_value':'12345678901234567890123.123456','reported_unit':'t/year','valid_from':'2025-01-01','evidence_reference':'synthetic exact precision fixture'}).json()
    target=new_database('imported')
    assert copy(client.app.state.engine.url.render_as_string(hide_password=False),target)['status']=='PASS'
    monkeypatch.setenv('DATABASE_URL',target)
    command.check(Config('alembic.ini'))
    imported=create_app(target,client.app.state.storage,write_token='test-token')
    with TestClient(imported) as other:
        other.headers['Authorization']='Bearer test-token'
        package=other.get('/api/export').json()
        assert package['records'][0]['record_id']==obs['id']
        assert package['records'][0]['normalized_value']=='12345678901234567890123.123456'
        assert package['records'][0]['content_hash']==doc['content_hash']
        assert package==client.get('/api/export').json()
        assert other.post('/api/resolve',json={'name':'TEST WORKS','country':'NO'}).json()['entity_id']==entity['id']
    imported.state.engine.dispose()

def test_separate_read_only_authorization(client):
    client.app.state.require_read_auth=True
    client.app.state.read_token='read-only-fixture'
    assert client.get('/api/health',headers={'Authorization':''}).status_code==200
    assert client.get('/api/workspace',headers={'Authorization':''}).status_code==401
    assert client.get('/api/workspace',headers={'Authorization':'Bearer read-only-fixture'}).status_code==200
    assert client.post('/api/entities',json={'name':'Unauthorized','country':'NO','facility_type':'smelter'},headers={'Authorization':'Bearer read-only-fixture'}).status_code==401

def test_independent_consumer_understands_export_without_database(client,example,tmp_path):
    import runpy
    entity,_,doc,_=example
    assert client.post('/api/observations',json={'entity_id':entity['id'],'document_id':doc['id'],'reported_value':'0.4','reported_unit':'Mt/year','valid_from':'2025-01-01','evidence_reference':'source table 1'}).status_code==201
    package=tmp_path/'evidence.json';package.write_text(json.dumps(client.get('/api/export').json()))
    consumer=runpy.run_path('scripts/consume_evidence.py')['consume']
    result=consumer(package,'app/evidence-v1.schema.json')
    assert result['records'][0]['value']=='400000'
    assert result['records'][0]['locator']=='source table 1'
    assert result['records'][0]['content_hash']==doc['content_hash']

def test_status_csv_frozen_replay_and_bad_status_rejection(client,example,tmp_path):
    from app.contract import freeze_v1,replay_v1
    _,_,_,payload=example
    csv='facility_name,country,reported_value,reported_unit,valid_from,valid_to,attribute,evidence_reference\nTest Works,NO,closed,status,2024-01-01,2024-12-31,status,row 2\nTest Works,NO,operating,status,2025-01-01,,status,row 3\n'
    doc=client.post('/api/documents',json={**payload,'media_type':'text/csv','content':csv}).json()
    response=client.post('/api/import/csv',json={'document_id':doc['id']})
    assert response.status_code==200,response.text
    with Session(client.app.state.engine) as session: freeze_v1(session,client.app.state.storage,tmp_path/'statuses.zip')
    assert replay_v1(tmp_path/'statuses.zip')['replayed_candidates']==2
    doc=client.post('/api/documents',json={**payload,'media_type':'text/csv','content':csv.replace('closed,status','invented,status')}).json()
    assert client.post('/api/import/csv',json={'document_id':doc['id']}).status_code==422

def test_unsafe_legacy_data_fails_before_an_import_target_exists(client,example,new_database):
    from sqlalchemy import create_engine,inspect
    from sqlalchemy.engine import make_url
    import pytest
    from tools.core_import import copy
    entity,_,doc,_=example
    obs=client.post('/api/observations',json={'entity_id':entity['id'],'document_id':doc['id'],'reported_value':'400','reported_unit':'kt/year','valid_from':'2025-01-01','evidence_reference':'synthetic migration fixture'}).json()
    source=client.app.state.engine.url.render_as_string(hide_password=False)
    with client.app.state.engine.begin() as connection:
        connection.execute(text("UPDATE observations SET reported_value='NaN' WHERE id=:id"),{'id':obs['id']})
    target=new_database('rejected')
    with pytest.raises(ValueError,match='unsafe exact numeric'):
        copy(source,target)
    if target.startswith('sqlite'): assert not Path(make_url(target).database).exists()
    else:
        engine=create_engine(target)
        assert not inspect(engine).get_table_names()
        engine.dispose()
    with client.app.state.engine.begin() as connection:
        connection.execute(text("UPDATE observations SET reported_value='400' WHERE id=:id"),{'id':obs['id']})
    assert copy(source,target)['status']=='PASS'
    assert client.get('/api/export').status_code==200

def test_contract_rejects_inconsistent_identity_metadata(client,example):
    from app.contract import validate_package
    from app.pipeline import logical_hash
    import pytest
    entity,_,doc,_=example
    client.post('/api/observations',json={'entity_id':entity['id'],'document_id':doc['id'],'reported_value':'400','reported_unit':'kt/year','valid_from':'2025-01-01','evidence_reference':'table 1'})
    package=client.get('/api/export').json();package['records'][0]['canonical_name']='Incorrect identity copy'
    package['build_hash']=logical_hash({k:v for k,v in package.items() if k!='build_hash'})
    with pytest.raises(ValueError,match='identity differs'): validate_package(package)

def test_rejected_build_still_exports_input_provenance_and_replays(client,example,tmp_path):
    from app.contract import freeze_v1,replay_v1
    _,_,_,payload=example
    doc=client.post('/api/documents',json={**payload,'content':'capacity 100 tonnes','media_type':'text/html'}).json()
    spec={'adapter':'html-v1','facility_name':'Unknown Elsewhere','country':'AU','valid_from':'2025-01-01','prefix':'capacity','suffix':'tonnes','unit':'t/year'}
    candidate=client.post('/api/documents/'+doc['id']+'/extract',json=spec).json()['candidates'][0]
    assert client.post('/api/reviews/'+candidate['review_id']+'/decision',json={'selected_entity_id':None,'reason':'Evidence cannot identify a trusted site'}).status_code==200
    package=client.get('/api/export').json()
    assert not package['records'] and package['documents'][0]['document_id']==doc['id']
    with Session(client.app.state.engine) as session: freeze_v1(session,client.app.state.storage,tmp_path/'rejected.zip')
    assert replay_v1(tmp_path/'rejected.zip')['replayed_candidates']==1

def parallel(jobs):
    """Start the jobs at the same moment, one thread each; the names of the exceptions they raised."""
    barrier,errors=threading.Barrier(len(jobs)),[]
    def run(job):
        barrier.wait()
        try: job()
        except Exception as exc: errors.append(type(exc).__name__)
    threads=[threading.Thread(target=run,args=(job,)) for job in jobs]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    return errors

def test_parallel_aliases_are_all_listed(client,example):
    entity,engine=example[0],client.app.state.engine
    def add(n):
        def job():
            with Session(engine) as session: add_alias(session,entity['id'],f'Parallel alias {n}','tester','parallel test');session.commit()
        return job
    assert parallel([add(n) for n in range(20)])==[]
    with Session(engine) as session:
        rows=session.scalars(select(EntityAlias.name).where(EntityAlias.entity_id==entity['id'])).all()
        assert len(rows)==21 and sorted(session.get(Entity,entity['id']).aliases)==sorted(rows)

def test_adding_a_lost_alias_again_lists_it(client,example):
    entity,engine=example[0],client.app.state.engine
    path=f"/api/entities/{entity['id']}/aliases"
    assert client.post(path,json={'name':'Lost Works','reason':'test alias'}).status_code==201
    with Session(engine) as session:
        # As a lost parallel write leaves it: the alias row exists, the list misses it.
        session.get(Entity,entity['id']).aliases=['Test Works'];session.commit()
    assert client.post(path,json={'name':'LOST WORKS','reason':'listed again'}).status_code==201
    with Session(engine) as session: assert session.get(Entity,entity['id']).aliases==['Test Works','Lost Works']

def test_opposite_supersessions_never_form_a_loop(client):
    engine=client.app.state.engine
    for n in range(10):
        a,b=(client.post('/api/entities',json={'name':f'Plant {side}{n}','country':'NO','facility_type':'smelter'}).json()['id'] for side in 'AB')
        def link(old,new):
            def job():
                with Session(engine) as session: supersede(session,old,new,'tester','parallel test');session.commit()
            return job
        assert parallel([link(a,b),link(b,a)])==['ValueError']
        with Session(engine) as session:
            assert len(session.scalars(select(EntitySupersession).where(EntitySupersession.old_entity_id.in_([a,b]))).all())==1

def test_quality_blocks_a_supersession_loop(client):
    a,b,c=(client.post('/api/entities',json={'name':f'Loop plant {n}','country':'NO','facility_type':'smelter'}).json()['id'] for n in range(3))
    with Session(client.app.state.engine) as session:
        # Written directly, as only a database without the supersession lock could have it.
        session.add_all([EntitySupersession(old_entity_id=old,new_entity_id=new,actor='tester',reason='loop fixture') for old,new in ((a,b),(b,a),(c,a))]);session.commit()
    findings=client.get('/api/quality').json()['findings']
    assert sorted(f['record_id'] for f in findings if f['code']=='SUPERSESSION_CYCLE')==sorted([a,b])

def test_write_access_needs_a_matching_bearer_token(client,monkeypatch):
    plant={'name':'Token test','country':'NO','facility_type':'smelter'}
    monkeypatch.setenv('WRITE_IDENTITIES_JSON','{"": "anyone"}')
    for header in ('','Bearer ','test-token','Token test-token','Bearer tést'.encode('latin-1')):
        assert client.post('/api/entities',json=plant,headers={'Authorization':header}).status_code==401,header
    assert client.post('/api/entities',json=plant,headers={'Authorization':'bearer test-token'}).status_code==201
    client.app.state.require_read_auth=True
    assert client.get('/api/workspace',headers={'Authorization':'Bearer tést'.encode('latin-1')}).status_code==401

def test_bad_request_values_are_refused_not_server_errors(client,example):
    entity,_,doc,payload=example
    for offset in ('100000000000000000000','9223372036854775808'):
        assert client.get('/api/records/entities?offset='+offset).status_code==422,offset
    assert client.get('/api/records/documents?version=100000000000000000000').status_code==422
    assert client.post('/api/entities',json={'name':'Nul\x00plant','country':'NO','facility_type':'smelter'}).status_code==422
    assert client.post('/api/sources',json={'name':'Nul\x00source','publisher':'P','source_type':'company','url':'https://example.org/'}).status_code==422
    assert client.post(f"/api/entities/{entity['id']}/aliases",json={'name':'Nul\x00alias','reason':'test case'}).status_code==422
    assert client.post('/api/resolve',json={'name':'Nul\x00plant'}).status_code==422
    # SQLite finds no such record; PostgreSQL cannot compare the text at all
    assert client.get('/api/records/entities/nul%00id').status_code in (404,422)
    assert client.get('/api/records/entities?name=a%00b').status_code==422
    observation={'entity_id':entity['id'],'document_id':doc['id'],'reported_unit':'t/year','valid_from':'2025-01-01','evidence_reference':'table 1'}
    for value in ('-0','1e3','1e-999999999','9e999999999','١٢٣'):
        assert client.post('/api/observations',json={**observation,'reported_value':value}).status_code==422,value
    company=client.post('/api/entities',json={'name':'Owner','kind':'company','country':'NO'}).json()
    link={'company_id':company['id'],'facility_id':entity['id'],'document_id':doc['id'],'valid_from':'2025-01-01','role':'OWNS','evidence_reference':'page 1 ownership'}
    for share in ('-0',-0.0):
        assert client.post('/api/relationships',json={**link,'percentage':share}).status_code==422,share
    assert client.get('/api/export').status_code==200
    csv='facility_name,country,reported_value,reported_unit,valid_from,evidence_reference\nTest Works,NO,400,kt/year,2025-01-01,'+'x'*140_000+'\n'
    large=client.post('/api/documents',json={**payload,'media_type':'text/csv','content':csv}).json()
    response=client.post('/api/import/csv',json={'document_id':large['id']})
    assert response.status_code==422 and 'Malformed CSV' in response.json()['detail']
    csv='facility_name,country,reported_value,reported_unit,valid_from,evidence_reference\nTest Works,NOR,400,kt/year,2025-01-01,table 2\n'
    wrong=client.post('/api/documents',json={**payload,'media_type':'text/csv','content':csv}).json()
    response=client.post('/api/import/csv',json={'document_id':wrong['id']})
    assert response.status_code==422 and 'two-letter' in response.json()['detail']
    # The refusal is recorded as a failed run, like any other bad file
    runs=client.get('/api/records/runs?status=failed').json()['records']
    assert any(run['manifest']['document_id']==wrong['id'] for run in runs)

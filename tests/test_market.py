"""Market data area: separate instruments, exact values from registered files, checks, export and replay.

All tables here are synthetic test data, not market prices.
"""
import io
import json
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.acquisition import register_bytes
from app.market import XLSX, freeze_market_v1, replay_market_v1, validate_market_package, export_market_v1
from app.models import InstrumentObservation, Run

LME = [{'code': 'LME_AL_CASH', 'name': 'LME Aluminium Cash', 'exchange': 'LME', 'market': 'forward', 'tenor': 'cash', 'currency': 'USD', 'unit': 'USD/t'},
       {'code': 'LME_AL_3M', 'name': 'LME Aluminium 3-Month', 'exchange': 'LME', 'market': 'forward', 'tenor': '3M', 'currency': 'USD', 'unit': 'USD/t'}]
SHFE = [{'code': 'SHFE_AL_2501', 'name': 'SHFE Aluminium Jan 2025', 'exchange': 'SHFE', 'market': 'futures', 'contract_code': 'AL2501', 'contract_month': '2025-01', 'currency': 'CNY', 'unit': 'CNY/t', 'quantity_unit': 'lots'},
        {'code': 'SHFE_AL_2502', 'name': 'SHFE Aluminium Feb 2025', 'exchange': 'SHFE', 'market': 'futures', 'contract_code': 'AL2502', 'contract_month': '2025-02', 'currency': 'CNY', 'unit': 'CNY/t', 'quantity_unit': 'lots'}]
# Shaped like a vendor export: two description lines, then the header. Synthetic values.
WIDE = ('Synthetic test export,,\nCurrency,U$,U$\nDate,LAHCASH,LAH3MTH\n'
        '02/01/2025,"2,500.5",2520\n03/01/2025,2510,2530.25\n06/01/2025,NA,2540\n')
WIDE_SPEC = {'adapter': 'market-csv-v1', 'header_row': 3, 'date_column': 'Date', 'date_format': '%d/%m/%Y', 'retrieved_at': '2025-01-07T09:30:00+01:00',
             'columns': [{'column': 'LAHCASH', 'instrument': 'LME_AL_CASH', 'price_type': 'official', 'field': 'settlement'},
                         {'column': 'LAH3MTH', 'instrument': 'LME_AL_3M', 'price_type': 'official', 'field': 'settlement'}]}
LONG = ('date,contract,month,open,high,low,close,settle,volume,oi\n'
        '2025-01-02,AL2501,202501,20000,20100,19950,20050,20040,1200,5000\n'
        '2025-01-02,AL2502,202502,20010,20120,19960,20060,20050,800,4000\n')
LONG_SPEC = {'adapter': 'market-csv-v1', 'date_column': 'date', 'date_format': '%Y-%m-%d', 'retrieved_at': '2025-01-03T00:00:00Z',
             'instrument_column': 'contract', 'instrument_map': {'AL2501': 'SHFE_AL_2501', 'AL2502': 'SHFE_AL_2502'},
             'contract_code_column': 'contract', 'contract_month_column': 'month',
             'columns': [{'column': c, 'price_type': 'daily', 'field': f} for c, f in
                         (('open', 'open'), ('high', 'high'), ('low', 'low'), ('close', 'close'), ('settle', 'settlement'), ('volume', 'volume'), ('oi', 'open_interest'))]}

def post(client, path, data, status=201):
    response = client.post('/api/' + path, json=data)
    assert response.status_code == status, response.text
    return response.json()

def source(client, synthetic=True, export_allowed=True):
    if synthetic:
        return post(client, 'sources', {'name': 'Synthetic market data', 'publisher': 'Test vendor', 'source_type': 'synthetic', 'url': 'https://example.org/vendor', 'access_status': 'synthetic'})
    created = post(client, 'sources', {'name': 'Licensed vendor data', 'publisher': 'Licensed vendor', 'source_type': 'commercial', 'url': 'https://example.org/licensed', 'access_status': 'review_required'})
    post(client, f"sources/{created['id']}/access", {'status': 'permitted', 'allowed_hosts': [], 'basis': 'University licence; club use and storage allowed', 'retention': 'Private storage only', 'export_allowed': export_allowed})
    return created

def table(client, source_record, content, url='https://example.org/vendor/export-1'):
    return post(client, 'documents', {'source_id': source_record['id'], 'title': 'Synthetic market export', 'original_url': url, 'published_at': '2025-01-07', 'media_type': 'text/csv', 'content': content})

def instruments(client, items):
    return [post(client, 'market/instruments', item) for item in items]

def test_instruments_keep_their_identity_and_refuse_inconsistent_definitions(client):
    cash, three = instruments(client, LME)
    assert cash['unit'] == 'USD/t' and three['tenor'] == '3M' and cash['commodity'] == 'aluminium'
    post(client, 'market/instruments', {**LME[0], 'code': 'X_WRONG', 'currency': 'CNY'}, 422)
    post(client, 'market/instruments', {**LME[0], 'code': 'X_NO_TENOR', 'tenor': None}, 422)
    post(client, 'market/instruments', {**SHFE[0], 'code': 'X_HALF', 'contract_month': None}, 422)
    post(client, 'market/instruments', {**LME[0], 'unit': 'USD/kg'}, 422)
    post(client, 'market/instruments', LME[0], 422)
    post(client, 'market/instruments', {'code': 'EUROPE_DUTY_PAID_PREMIUM', 'name': 'Europe duty-paid premium', 'market': 'physical', 'region': 'Europe', 'currency': 'USD', 'unit': 'USD/t'})

def test_wide_vendor_table_becomes_separate_exact_observations(client):
    instruments(client, LME)
    doc = table(client, source(client), WIDE)
    result = post(client, f"documents/{doc['id']}/market-import", WIDE_SPEC)
    assert result['observations'] == 5 and not result['duplicate']
    rows = client.get('/api/records/instrument_observations', params={'limit': 100}).json()['records']
    by_key = {(r['instrument_id'], r['effective_date']): r for r in rows}
    cash = client.get('/api/records/instruments', params={'code': 'LME_AL_CASH'}).json()['records'][0]
    first = by_key[(cash['id'], '2025-01-02')]
    assert first['settlement'] == '2500.5' and first['bid'] is None and first['price_type'] == 'official'
    assert first['retrieved_at'] == '2025-01-07T08:30:00Z' and first['data_status'] == 'reported' and first['published_at'] is None
    assert first['source_series'] == {'settlement': 'LAHCASH'} and first['evidence_reference'] == 'CSV row 4; columns LAHCASH'
    assert (cash['id'], '2025-01-06') not in by_key  # NA is a missing value, never a zero
    summary = {item['code']: item for item in client.get('/api/market/summary').json()['instruments']}
    assert (summary['LME_AL_3M']['observations'], summary['LME_AL_3M']['first_date'], summary['LME_AL_3M']['last_date']) == (3, '2025-01-02', '2025-01-06')
    assert summary['LME_AL_3M']['latest'][0]['values'] == {'settlement': '2540'} and summary['LME_AL_CASH']['last_date'] == '2025-01-03'
    again = post(client, f"documents/{doc['id']}/market-import", WIDE_SPEC)
    assert again['duplicate'] and again['build']['id'] == result['build']['id']
    assert client.get('/api/records/instrument_observations').json()['total'] == 5
    assert client.post(f"/api/market/builds/{result['build']['id']}/replay").json()['equivalent']

def test_long_table_with_contracts_volume_and_open_interest(client):
    instruments(client, SHFE)
    result = post(client, f"documents/{table(client, source(client), LONG)['id']}/market-import", LONG_SPEC)
    assert result['observations'] == 2
    rows = client.get('/api/records/instrument_observations').json()['records']
    jan = next(r for r in rows if r['contract_code'] == 'AL2501')
    assert (jan['contract_month'], jan['open'], jan['high'], jan['settlement'], jan['volume'], jan['open_interest']) == ('2025-01', '20000', '20100', '20040', '1200', '5000')

@pytest.mark.parametrize('content,message', [
    (LONG.replace('20100,19950', '19900,19950'), 'high is below low'),
    (LONG.replace(',1200,', ',-5,'), 'volume is negative'),
    (LONG.replace('20040', '20040.1234567'), '6 decimal digits'),
    (LONG.replace('20040', '2e4'), 'is not a number'),
    (LONG.replace('20040', '1' + '0' * 30), '24 integer'),
    (LONG.replace('2025-01-02,AL2501', '02.01.2025,AL2501'), 'does not match'),
    (LONG.replace('AL2502,202502', 'AL2503,202503'), 'not in instrument_map'),
    (LONG + '2025-01-02,AL2501,202501,1,1,1,1,1,1,1\n', 'a second open')])
def test_bad_tables_are_refused_whole_and_logged(client, content, message):
    instruments(client, SHFE)
    response = client.post(f"/api/documents/{table(client, source(client), content)['id']}/market-import", json=LONG_SPEC)
    assert response.status_code == 422 and message in response.json()['detail']
    assert client.get('/api/records/instrument_observations').json()['total'] == 0
    with Session(client.app.state.engine) as s:
        assert s.scalars(select(Run).where(Run.status == 'failed')).all()

def test_unknown_instruments_and_missing_quantity_units_are_refused(client):
    doc = table(client, source(client), LONG)
    assert 'Register these instruments first: SHFE_AL_2501, SHFE_AL_2502' in client.post(f"/api/documents/{doc['id']}/market-import", json=LONG_SPEC).json()['detail']
    instruments(client, [{**item, 'quantity_unit': None} for item in SHFE])
    assert 'no quantity_unit' in client.post(f"/api/documents/{doc['id']}/market-import", json=LONG_SPEC).json()['detail']

def test_database_refuses_impossible_market_values(client):
    instruments(client, SHFE)
    post(client, f"documents/{table(client, source(client), LONG)['id']}/market-import", LONG_SPEC)
    for statement in ("UPDATE market_observation SET low = '99999'", "UPDATE market_observation SET volume = '-1'",
                      "UPDATE market_observation SET open=NULL, high=NULL, low=NULL, close=NULL, settlement=NULL, volume=NULL, open_interest=NULL",
                      "UPDATE market_observation SET data_status = 'guessed'"):
        with client.app.state.engine.begin() as connection, pytest.raises(IntegrityError):
            connection.execute(text(statement))

def test_quality_counts_series_problems_without_changing_data(client):
    instruments(client, LME)
    vendor = source(client)
    content = ('Date,LAHCASH\n2025-01-03,2500\n2025-01-04,2500\n2025-01-06,2500\n2025-02-03,2510\n2025-02-04,3500\n')
    post(client, f"documents/{table(client, vendor, content)['id']}/market-import", {**WIDE_SPEC, 'header_row': 1, 'date_format': '%Y-%m-%d', 'columns': WIDE_SPEC['columns'][:1]})
    other = 'Date,LAHCASH\n2025-01-03,2499\n'
    post(client, f"documents/{table(client, vendor, other, 'https://example.org/vendor/export-2')['id']}/market-import", {**WIDE_SPEC, 'header_row': 1, 'date_format': '%Y-%m-%d', 'columns': WIDE_SPEC['columns'][:1]})
    report = client.get('/api/market/quality').json()
    found = {f['code']: f for f in report['findings']}
    assert report['status'] == 'WARN' and report['coverage']['observations'] == 6
    assert found['WEEKEND_DATE']['examples'] == ['2025-01-04'] and found['WEEKEND_DATE']['record_id'] == 'LME_AL_CASH/official'
    assert found['POSSIBLE_CARRY_FORWARD']['count'] == 2
    assert found['SERIES_GAP']['examples'] == ['2025-02-03'] and found['SUSPICIOUS_VALUE_CHANGE']['examples'] == ['2025-02-04']
    assert found['CONFLICTING_OBSERVATIONS']['examples'] == ['2025-01-03'] and found['PUBLICATION_TIME_UNKNOWN']['severity'] == 'INFO'
    assert client.get('/api/records/instrument_observations').json()['total'] == 6
    open_interest = 'date,contract,month,settle,oi\n2025-01-02,AL2501,202501,20040,5000\n2025-01-03,AL2501,202501,20040,5100\n2025-01-06,AL2501,202501,20040,5100\n'
    spec = {**LONG_SPEC, 'instrument_map': {'AL2501': 'SHFE_AL_2501'}, 'columns': [c for c in LONG_SPEC['columns'] if c['column'] in ('settle', 'oi')]}
    instruments(client, SHFE[:1])
    post(client, f"documents/{table(client, vendor, open_interest, 'https://example.org/vendor/export-3')['id']}/market-import", spec)
    repeated = next(f for f in client.get('/api/market/quality').json()['findings'] if f['code'] == 'POSSIBLE_CARRY_FORWARD' and f['record_id'].startswith('SHFE'))
    assert repeated['examples'] == ['2025-01-06']  # same settlement but changed open interest on 01-03 is real trading

def test_export_is_self_contained_and_leaves_internal_sources_out(client):
    instruments(client, LME + SHFE)
    post(client, f"documents/{table(client, source(client), LONG)['id']}/market-import", LONG_SPEC)
    licensed = source(client, synthetic=False, export_allowed=False)
    post(client, f"documents/{table(client, licensed, WIDE, 'https://example.org/licensed/export')['id']}/market-import", WIDE_SPEC)
    assert any(f['code'] == 'EXPORT_WITHHELD' for f in client.get('/api/market/quality').json()['findings'])
    package = client.get('/api/market/export').json()
    assert [w['observations'] for w in package['withheld']] == [5] and len(package['observations']) == 2
    item = package['observations'][0]
    assert (item['instrument_code'], item['exchange'], item['currency'], item['unit'], item['quantity_unit'], item['contract_month']) == ('SHFE_AL_2501', 'SHFE', 'CNY', 'CNY/t', 'lots', '2025-01')
    assert item['synthetic'] and item['content_hash'] == package['documents'][0]['content_hash'] and item['retrieved_at'] == '2025-01-03T00:00:00Z'
    assert client.get('/api/market/export', params={'instrument': 'SHFE_AL_2502'}).json()['observations'][0]['instrument_code'] == 'SHFE_AL_2502'
    assert client.get('/api/market/export', params={'from': '2025-01-03'}).json()['observations'] == []
    assert client.get('/api/market/export', params={'instrument': 'NOPE'}).status_code == 422
    assert client.get('/api/market/export/schema').json()['title'] == 'MarketDataPackage 1.0.0'
    for field in ('trading_signal', 'cash_3m_signal', 'all_in_price'):
        changed = json.loads(json.dumps(package)); changed['observations'][0][field] = 1
        with pytest.raises(ValueError, match='prohibited'): validate_market_package(changed)
    tampered = json.loads(json.dumps(package)); tampered['observations'][0]['settlement'] = '1'
    with pytest.raises(ValueError, match='hash'): validate_market_package(tampered)

def test_re_review_keeps_data_internal_unless_export_is_decided_again(client):
    licensed = source(client, synthetic=False, export_allowed=False)
    again = post(client, f"sources/{licensed['id']}/access", {'status': 'permitted', 'allowed_hosts': [], 'basis': 'Licence re-checked with the holder', 'retention': 'Private storage only'})
    assert again['export_allowed'] is False
    allowed = post(client, f"sources/{licensed['id']}/access", {'status': 'permitted', 'allowed_hosts': [], 'basis': 'Licence holder confirmed export in writing', 'retention': 'Private storage only', 'export_allowed': True})
    assert allowed['export_allowed'] is True

def test_facility_facts_may_not_cite_internal_sources(client, example):
    entity, _, _, payload = example
    licensed = source(client, synthetic=False, export_allowed=False)
    doc = post(client, 'documents', {**payload, 'source_id': licensed['id'], 'original_url': 'https://example.org/licensed/plants'})
    post(client, 'observations', {'entity_id': entity['id'], 'document_id': doc['id'], 'reported_value': '400', 'reported_unit': 'kt/year', 'valid_from': '2025-01-01', 'evidence_reference': 'row 1'})
    assert 'EXPORT_NOT_ALLOWED' in [f['code'] for f in client.get('/api/quality').json()['findings']]
    assert client.get('/api/export').status_code == 422

def test_damaged_files_block_export_and_frozen_bundles_replay(client, tmp_path):
    instruments(client, SHFE)
    doc = table(client, source(client), LONG)
    post(client, f"documents/{doc['id']}/market-import", LONG_SPEC)
    with Session(client.app.state.engine) as s:
        storage = client.app.state.storage
        bundle = tmp_path / 'market.zip'
        build_hash = freeze_market_v1(s, storage, bundle)
        assert replay_market_v1(bundle) == {'equivalent': True, 'build_hash': build_hash, 'builds': 1, 'observations': 2}
        observation = s.scalars(select(InstrumentObservation)).first()
        observation.settlement = 1; s.commit()
        with pytest.raises(ValueError, match='differs from the frozen document'): export_market_v1(s, storage)
    (client.app.state.storage / doc['content_hash']).write_bytes(b'damaged')
    assert client.get('/api/market/quality').json()['status'] == 'FAIL'
    assert client.get('/api/market/export').status_code == 422

def test_xlsx_tables_are_read_from_the_registered_workbook(client):
    from openpyxl import Workbook
    from datetime import datetime
    instruments(client, LME)
    book = Workbook(); sheet = book.active; sheet.title = 'Prices'
    sheet.append(['Synthetic test workbook']); sheet.append(['Date', 'LAHCASH', 'LAH3MTH'])
    sheet.append([datetime(2025, 1, 2), 2500.5, 2520]); sheet.append([datetime(2025, 1, 3), None, 2530.25])
    buffer = io.BytesIO(); book.save(buffer)
    with Session(client.app.state.engine) as s:
        vendor = source(client)
        doc, _ = register_bytes(s, client.app.state.storage, {'source_id': vendor['id'], 'title': 'Synthetic workbook', 'original_url': 'https://example.org/vendor/book', 'published_at': None, 'media_type': XLSX}, buffer.getvalue())
        s.commit(); doc_id = doc.id
    spec = {**WIDE_SPEC, 'adapter': 'market-xlsx-v1', 'sheet': 'Prices', 'header_row': 2, 'date_format': '%Y-%m-%d'}
    result = post(client, f'documents/{doc_id}/market-import', spec)
    assert result['observations'] == 3
    values = sorted(r['settlement'] for r in client.get('/api/records/instrument_observations').json()['records'])
    assert values == ['2500.5', '2520', '2530.25']
    assert client.post(f'/api/documents/{doc_id}/market-import', json={**spec, 'sheet': 'Missing'}).status_code == 422
    assert client.post(f'/api/documents/{doc_id}/market-import', json={**spec, 'sheet': None}).status_code == 422

def test_command_line_registers_a_file_with_its_instruments(client, tmp_path):
    from tools import market_import
    vendor = source(client)
    path = tmp_path / 'export.csv'; path.write_text(WIDE)
    url = client.app.state.engine.url.render_as_string(hide_password=False)
    common = dict(source_id=vendor['id'], locator='vendor:synthetic-export', title='Synthetic export', spec=WIDE_SPEC, instruments=LME,
                  storage=client.app.state.storage, database_url=url)
    first = market_import.run(path, **common)
    assert first['instruments_created'] == ['LME_AL_CASH', 'LME_AL_3M'] and first['observations'] == 5 and first['quality']['status'] == 'PASS'
    again = market_import.run(path, **common)
    assert again['duplicate_document'] and again['duplicate_build'] and not again['instruments_created']
    with pytest.raises(ValueError, match='different definition'): market_import.run(path, **{**common, 'instruments': [{**LME[0], 'name': 'Renamed'}]})
    with pytest.raises(ValueError, match='locator'): market_import.run(path, **{**common, 'locator': 'not a uri'})

# Shaped like an LSEG historical-pricing download: request parts with the API's headers and rows. Synthetic.
LSEG = [{'chunk': ['2025-01-01', '2025-01-02'], 'raw': {'universe': {'ric': 'TESTc1'}, 'headers': [{'name': 'DATE'}, {'name': 'SETTLE'}, {'name': 'BID'}, {'name': 'ASK'}, {'name': 'OPINT_1'}, {'name': 'CRT_MNTH'}],
         'data': [['2025-01-02', 0.12345, 0.11, 0.13, 4321, 202501], ['2025-01-01', 7e-05, None, None, None, None]]}},
        {'chunk': ['2025-01-03', '2025-01-03'], 'raw': {'universe': {'ric': 'TESTc1'}, 'headers': [{'name': 'DATE'}, {'name': 'SETTLE'}, {'name': 'BID'}, {'name': 'ASK'}, {'name': 'OPINT_1'}, {'name': 'CRT_MNTH'}],
         'data': [['2025-01-03', 1.23456, None, None, 3333, 202502]]}}]
LSEG_SPEC = {'adapter': 'market-lseg-json-v1', 'date_column': 'DATE', 'date_format': '%Y-%m-%d', 'retrieved_at': '2026-10-26T21:48:47Z', 'contract_month_column': 'CRT_MNTH',
             'columns': [{'column': c, 'instrument': 'CME_AUP_FRONT', 'price_type': 'daily', 'field': f, 'source_series': 'TESTc1 ' + c}
                         for c, f in (('SETTLE', 'settlement'), ('BID', 'bid'), ('ASK', 'ask'), ('OPINT_1', 'open_interest'))]}
AUP = {'code': 'CME_AUP_FRONT', 'name': 'US Midwest premium futures, front month', 'exchange': 'CME', 'market': 'futures', 'tenor': 'front', 'region': 'US Midwest',
       'currency': 'USD', 'unit': 'USD/lb', 'quantity_unit': 'contracts'}

def lseg_document(client, parts=LSEG):
    with Session(client.app.state.engine) as s:
        doc, _ = register_bytes(s, client.app.state.storage, {'source_id': source(client)['id'], 'title': 'Synthetic LSEG response', 'original_url': 'lseg:TESTc1',
                                                              'published_at': None, 'media_type': 'application/json'}, json.dumps(parts).encode())
        s.commit()
        return doc.id

def test_lseg_responses_are_read_exactly_across_their_parts(client):
    instruments(client, [AUP])
    result = post(client, f'documents/{lseg_document(client)}/market-import', LSEG_SPEC)
    assert result['observations'] == 3
    rows = {r['effective_date']: r for r in client.get('/api/records/instrument_observations').json()['records']}
    assert (rows['2025-01-02']['settlement'], rows['2025-01-02']['bid'], rows['2025-01-02']['open_interest'], rows['2025-01-02']['contract_month']) == ('0.12345', '0.11', '4321', '2025-01')
    assert rows['2025-01-01']['settlement'] == '0.00007' and rows['2025-01-01']['bid'] is None and rows['2025-01-01']['contract_month'] is None
    assert rows['2025-01-03']['evidence_reference'] == 'Response part 2 row 1; columns SETTLE, OPINT_1'
    assert rows['2025-01-02']['source_series'] == {'settlement': 'TESTc1 SETTLE', 'bid': 'TESTc1 BID', 'ask': 'TESTc1 ASK', 'open_interest': 'TESTc1 OPINT_1'}
    assert client.post(f"/api/market/builds/{result['build']['id']}/replay").json()['equivalent']

@pytest.mark.parametrize('parts,message', [
    ({'not': 'a list'}, 'list of LSEG response parts'),
    ([{'raw': {'headers': [{'name': 'DATE'}]}}], 'no headers and data'),
    ([LSEG[0], {'raw': {**LSEG[1]['raw'], 'headers': LSEG[1]['raw']['headers'][:-1]}}], 'other columns than part 1'),
    ([{'raw': {**LSEG[0]['raw'], 'data': [['2025-01-02', 1]]}}], 'does not match the headers'),
    ([{'raw': {**LSEG[0]['raw'], 'data': [['2025-01-02', 1e30, None, None, None, None]]}}], '24 integer')])
def test_malformed_lseg_responses_are_refused(client, parts, message):
    instruments(client, [AUP])
    response = client.post(f'/api/documents/{lseg_document(client, parts)}/market-import', json=LSEG_SPEC)
    assert response.status_code == 422 and message in response.json()['detail']
    assert client.post(f'/api/documents/{lseg_document(client)}/market-import', json={**LSEG_SPEC, 'header_row': 2}).status_code == 422

# Shaped like a table copied from a vendor screen: tab-separated, a title line, repeated column names. Synthetic.
SCREEN = ('\nPane 1\nDate\tSynthetic 99.7% \tSynthetic 99.7% \tSynthetic 99.7% \n'
          '01/07/2010\t1500\t1501\t1503\n02/07/2010\t1510\t1512\t1508\n05/07/2010\t1520\t1519\t1522\n')
SCREEN_SPEC = {'adapter': 'market-csv-v1', 'header_row': 3, 'date_column': 'Date', 'date_format': '%d/%m/%Y', 'retrieved_at': '2026-10-27T13:09:12+01:00',
               'missing_values': ['', 'n/a'], 'leave_out': {'2010-07-02': 'official buyer above seller as delivered'}, 'status_by_date': {'2010-07-05': 'provisional'},
               'columns': [{'column': '#3', 'instrument': 'LME_AL_3M', 'price_type': 'official', 'field': 'bid', 'source_series': 'LAH3MTH(OB)'},
                           {'column': '#4', 'instrument': 'LME_AL_3M', 'price_type': 'official', 'field': 'ask', 'source_series': 'LAH3MTH(OO)'}]}

def screen_document(client, content=SCREEN):
    with Session(client.app.state.engine) as s:
        doc, _ = register_bytes(s, client.app.state.storage, {'source_id': source(client)['id'], 'title': 'Synthetic screen copy', 'original_url': 'datastream:synthetic',
                                                              'published_at': None, 'media_type': 'text/tab-separated-values'}, content.encode())
        s.commit()
        return doc.id

def test_screen_copies_with_repeated_names_are_read_by_position(client):
    instruments(client, LME)
    result = post(client, f'documents/{screen_document(client)}/market-import', SCREEN_SPEC)
    rows = {r['effective_date']: r for r in client.get('/api/records/instrument_observations').json()['records']}
    assert result['observations'] == 2 and '2010-07-02' not in rows
    assert (rows['2010-07-01']['bid'], rows['2010-07-01']['ask'], rows['2010-07-01']['data_status']) == ('1501', '1503', 'reported')
    assert rows['2010-07-05']['data_status'] == 'provisional' and rows['2010-07-05']['evidence_reference'] == 'TSV row 6; columns #3, #4'
    left = next(f for f in client.get('/api/market/quality').json()['findings'] if f['code'] == 'ROWS_LEFT_OUT')
    assert left['examples'] == ['2010-07-02'] and 'buyer above seller' in left['message']
    assert client.post(f"/api/market/builds/{result['build']['id']}/replay").json()['equivalent']

@pytest.mark.parametrize('change,message', [
    ({'leave_out': {}}, 'bid is above ask'),
    ({'leave_out': {'2010-07-02': 'reason given', '2011-01-03': 'not in the file'}}, 'not in the table: 2011-01-03'),
    ({'status_by_date': {'2012-01-02': 'provisional'}}, 'not in the table: 2012-01-02'),
    ({'columns': [{**SCREEN_SPEC['columns'][0], 'column': '#9'}]}, 'beyond the 4 columns'),
    ({'columns': [{**SCREEN_SPEC['columns'][0], 'column': 'Synthetic 99.7%'}]}, 'exactly once')])
def test_screen_copy_rules_are_checked(client, change, message):
    instruments(client, LME)
    response = client.post(f'/api/documents/{screen_document(client)}/market-import', json={**SCREEN_SPEC, **change})
    assert response.status_code == 422 and message in response.json()['detail']
    assert client.post(f'/api/documents/{screen_document(client)}/market-import', json={**SCREEN_SPEC, 'leave_out': {'2010-07-02': ''}}).status_code == 422

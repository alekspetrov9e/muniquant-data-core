"""tools/lseg_import.py: an LSEG export folder becomes separate instruments and observations, kept internal.

The export below is synthetic and shaped like the lseg-data downloads (manifest plus untouched responses)."""
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Instrument, InstrumentObservation, SourceAccess
from tools import lseg_import

def response(ric, headers, rows):
    return [{'chunk': [rows[-1][0], rows[0][0]], 'raw': {'universe': {'ric': ric}, 'headers': [{'name': name} for name in ['DATE', *headers]], 'data': rows}}]

FILES = {
    'shfe_aluminium_contracts/SAFF5_1_1d_EXCHDATE_2015-2015': ('SAFF5^1', '2015-01', ['TRDPRC_1', 'HIGH_1', 'LOW_1', 'SETTLE', 'ACVOL_UNS', 'OPINT_1', 'SETL_PCHNG'],
                                                              [['2015-01-06', 13900, 13950, 13850, 13910, 120, 800, 0.1], ['2015-01-05', 13880, None, None, 13890, 100, 790, None]]),
    'premiums/AUPc1_1d_EXCHDATE_2015-2015': ('AUPc1', None, ['HIGH_1', 'LOW_1', 'SETTLE', 'OPINT_1', 'CRT_MNTH'],
                                             [['2015-07-17', 0.05, 0.06, 0.05512, 4242, None], ['2015-07-16', 0.05, None, 0.055, 4242, 201507]]),
    'alumina/SMM-ALM-FOB_1d_EXCHDATE_2015-2015': ('SMM-ALM-FOB', None, ['TRDPRC_1', 'HIGH_1', 'LOW_1'], [['2015-01-05', 351.5, 355, 348]]),
    'facilities/physical_assets_smelter': ('PHYSICAL_ASSETS search', None, [], [])}

def export(tmp_path):
    folder = tmp_path / 'export'
    jobs = []
    for name, (ric, month, headers, rows) in FILES.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        if rows: (folder / (name + '.raw.json')).write_text(json.dumps(response(ric, headers, rows)))
        jobs.append({'code': ric, 'contract_month': month, 'status': 'ok', 'file': name + '.csv', 'columns': headers})
    jobs.append({'code': 'SAFcv1', 'status': 'no_data', 'note': 'UserNotPermission'})
    (folder / 'manifest.json').write_text(json.dumps({'created_utc': '2026-10-26T21:48:47Z', 'jobs': jobs}))
    return folder

def test_export_folder_loads_as_internal_market_data(client, tmp_path):
    folder = export(tmp_path)
    url, storage = client.app.state.engine.url.render_as_string(hide_password=False), client.app.state.storage
    plan = lseg_import.run(folder, dry_run=True, storage=storage, database_url=url)
    assert plan['instruments'] == ['CME_AUP_FRONT', 'SHFE_AL_1501', 'SMM_ALUMINA_FOB_AUSTRALIA'] and [s['code'] for s in plan['skipped']] == ['PHYSICAL_ASSETS search', 'SAFcv1']
    result = lseg_import.run(folder, storage=storage, database_url=url)
    assert (result['documents'], result['builds'], result['observations'], result['instruments_created']) == (3, 3, 5, 3)
    with Session(client.app.state.engine) as s:
        assert s.scalar(select(SourceAccess).where(SourceAccess.source_id == result['source_id'])).export_allowed is False
        codes = {i.id: i for i in s.scalars(select(Instrument))}
        shfe = next(i for i in codes.values() if i.code == 'SHFE_AL_1501')
        assert (shfe.contract_code, shfe.contract_month, shfe.unit, shfe.quantity_unit) == ('al1501', '2015-01', 'CNY/t', 'contracts')
        rows = {(codes[o.instrument_id].code, o.effective_date.isoformat()): o for o in s.scalars(select(InstrumentObservation))}
        first = rows[('SHFE_AL_1501', '2015-01-06')]
        assert (str(first.close), str(first.high), str(first.settlement), str(first.volume)) == ('13900', '13950', '13910', '120')
        assert first.source_series['settlement'] == 'SAFF5^1 SETTLE' and first.price_type == 'daily'
        aup = rows[('CME_AUP_FRONT', '2015-07-17')]
        assert aup.high is None and aup.low is None and str(aup.settlement) == '0.05512'  # high/low of AUPc1 are left out
        assert rows[('CME_AUP_FRONT', '2015-07-16')].contract_month == '2015-07'
        assert rows[('SMM_ALUMINA_FOB_AUSTRALIA', '2015-01-05')].price_type == 'assessment'
    assert client.get('/api/market/export').json()['withheld'][0]['observations'] == 5
    again = lseg_import.run(folder, storage=storage, database_url=url)
    assert (again['documents'], again['duplicate_documents'], again['builds'], again['observations']) == (0, 3, 0, 0)

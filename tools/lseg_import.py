"""Load an LSEG export folder (lseg-data historical-pricing downloads) into the market data area.

The folder holds manifest.json and, per series, the untouched API response (*.raw.json) next to a
pandas CSV dump. The untouched response is the evidence: each is registered unchanged under its
SHA-256 and read by the market-lseg-json-v1 adapter. Instruments come from the mapping below; every
unit is the exchange's or publisher's own quotation, named in the instrument description.

    python -m tools.lseg_import EXPORT_DIR [--dry-run] [--actor NAME]

The LSEG source is registered on first use with an access decision that keeps its data inside the
Core (export_allowed false): the licence allows academic use by the project group only. Physical-asset
lists are vendor hints, never Core facts, and are not loaded. Uses DATABASE_URL and SNAPSHOT_DIR.
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import DATABASE_URL, make_engine
from app.market import inspect_market_quality
from app.models import Audit, Source, SourceAccess
from tools import market_import

SOURCE = {'name': 'LSEG Workspace exports (lseg-data API)', 'publisher': 'LSEG', 'source_type': 'commercial', 'url': 'https://www.lseg.com/en/data-analytics',
          'notes': 'Daily market data exported by a project member through LSEG Workspace (TUM chair licence). Files handed over unchanged.'}
ACCESS = {'basis': 'LSEG Workspace via TUM chair: academic use only, project group only; do not publish or pass on the raw data (licence note in the export README)',
          'retention': 'Private storage only; never in git; no export until onward use is confirmed in writing'}
# LSEG field → observation field, for daily summaries. Changes, limits, VWAP, mid prices and totals
# across contract months are left out: derived values or other series.
DAILY = {'TRDPRC_1': 'close', 'OPEN_PRC': 'open', 'HIGH_1': 'high', 'LOW_1': 'low', 'BID': 'bid', 'ASK': 'ask', 'SETTLE': 'settlement',
         'ACVOL_UNS': 'volume', 'OPINT_1': 'open_interest'}
ASSESSMENT = {'TRDPRC_1': 'close', 'HIGH_1': 'high', 'LOW_1': 'low'}
# Columns a file cannot keep: AUPc1 has one row with high below low (2015-07-17), which the Core refuses.
LEAVE_OUT = {'AUPc1': {'HIGH_1', 'LOW_1'}}
MONTHS = 'FGHJKMNQUVXZ'
TENORS = {'1': 'front', '2': 'second', '3': 'third'}
SHFE = {'exchange': 'SHFE', 'market': 'futures', 'currency': 'CNY', 'unit': 'CNY/t', 'quantity_unit': 'contracts'}
CME = {'exchange': 'CME', 'market': 'futures', 'currency': 'USD', 'quantity_unit': 'contracts'}
VOLUME = ' Volume and open interest are LSEG ACVOL_UNS and OPINT_1, numbers of contracts.'
PREMIUMS = {
    'AUP': ('CME_AUP', 'US Midwest premium futures (CME AUP, Platts)', 'US Midwest', 'USD/lb', 'Quoted in US dollars per pound (COMEX rulebook chapter 1189).'),
    'EPD': ('CME_EDP', 'Europe duty-paid premium futures (CME EDP, Fastmarkets/Metal Bulletin)', 'Europe, duty-paid Rotterdam', 'USD/t', 'Quoted in US dollars per metric ton (CME EDP fact sheet). LSEG root EPD.'),
    'AEP': ('CME_AEP', 'Europe duty-unpaid premium futures (CME AEP, Fastmarkets/Metal Bulletin)', 'Europe, duty-unpaid Rotterdam', 'USD/t', 'Settles on a $/tonne assessment (COMEX rulebook chapter 108).'),
    'PJM': ('CME_MJP', 'Japan premium futures (CME MJP, Platts)', 'Japan', 'USD/t', 'Settles on the Platts CIF Japan premium in $/mt (COMEX rulebook chapter 109). LSEG root PJM.')}

def plan(job):
    """(instrument definition, field map, price type, extra settings) for one manifest entry, or None to skip."""
    folder, ric = job['file'].split('/')[0], job['code']
    if folder == 'shfe_aluminium_contracts':
        year, month = job['contract_month'].split('-')
        code = year[2:] + month
        return ({**SHFE, 'code': 'SHFE_AL_' + code, 'name': f"SHFE aluminium {job['contract_month']}", 'commodity': 'aluminium', 'contract_code': 'al' + code,
                 'contract_month': job['contract_month'], 'description': f'LSEG RIC {ric}. Prices in CNY/t as SHFE quotes them.' + VOLUME}, DAILY, 'daily', {})
    if folder == 'comex_aluminium_contracts':
        year, month = job['contract_month'].split('-')
        return ({**CME, 'code': 'CME_ALI_' + year[2:] + month, 'name': f"COMEX aluminium {job['contract_month']}", 'commodity': 'aluminium', 'unit': 'USD/t',
                 'contract_code': 'ALI' + MONTHS[int(month) - 1] + year[2:], 'contract_month': job['contract_month'],
                 'description': f'LSEG RIC {ric}. Prices in USD/t as COMEX quotes them.' + VOLUME}, DAILY, 'daily', {})
    match = re.fullmatch(r'(SAF|SAO|AUP|EPD|AEP|PJM)c([1-3])', ric)
    if match and folder in ('shfe_aluminium_continuations', 'alumina', 'premiums'):
        root, tenor = match[1], TENORS[match[2]]
        if root in ('SAF', 'SAO'):
            commodity, name = ('aluminium', 'aluminium') if root == 'SAF' else ('alumina', 'alumina')
            return ({**SHFE, 'code': f"SHFE_{'AL' if root == 'SAF' else 'AO'}_{tenor.upper()}", 'name': f'SHFE {name}, {tenor} contract (continuation)', 'commodity': commodity,
                     'tenor': tenor, 'description': f'LSEG RIC {ric}, continuation; the actual contract is not in the data. Prices in CNY/t as SHFE quotes them.' + VOLUME},
                    DAILY, 'daily', {})
        prefix, name, region, unit, quoted = PREMIUMS[root]
        return ({**CME, 'code': f'{prefix}_{tenor.upper()}', 'name': f'{name}, {tenor} month (continuation)', 'commodity': 'aluminium', 'region': region, 'unit': unit,
                 'tenor': tenor, 'description': f'LSEG RIC {ric}, continuation; CRT_MNTH names the contract month where given. {quoted}' + VOLUME},
                DAILY, 'daily', {'contract_month_column': 'CRT_MNTH'})
    if ric == 'SMM-ALM-FOB':
        return ({'code': 'SMM_ALUMINA_FOB_AUSTRALIA', 'name': 'SMM Australian alumina FOB', 'market': 'physical', 'commodity': 'alumina', 'region': 'Australia (FOB)',
                 'currency': 'USD', 'unit': 'USD/t', 'description': 'LSEG RIC SMM-ALM-FOB, Shanghai Metals Market assessment; SMM quotes it in US$/t. close = LSEG TRDPRC_1.'},
                ASSESSMENT, 'assessment', {})
    return None

def response_columns(path):
    """The column names the untouched response itself carries (part 1), not the manifest's request list."""
    parts = json.loads(path.read_text())
    return [item['name'] for item in parts[0]['raw']['headers']]

def settings(job, columns, fields, price_type, extra, instrument, retrieved_at):
    present = [column for column in columns if column in fields and column not in LEAVE_OUT.get(job['code'], set())]
    if not present: raise ValueError(f"{job['code']}: none of the mapped columns is in the file")
    mapped = [{'column': column, 'instrument': instrument['code'], 'price_type': price_type, 'field': fields[column], 'source_series': f"{job['code']} {column}"} for column in present]
    extra = {key: value for key, value in extra.items() if value in columns}
    return {'adapter': 'market-lseg-json-v1', 'date_column': 'DATE', 'date_format': '%Y-%m-%d', 'retrieved_at': retrieved_at, 'columns': mapped, **extra}

def ensure_source(s, actor):
    source = s.scalar(select(Source).where(Source.name == SOURCE['name']))
    if not source:
        source = Source(**SOURCE, access_status='permitted'); s.add(source); s.flush()
        decision = SourceAccess(source_id=source.id, status='permitted', allowed_hosts=[], export_allowed=False, reviewer=actor, **ACCESS); s.add(decision); s.flush()
        s.add(Audit(actor=actor, action='access_decision', record_id=decision.id, detail={'type': 'source_access', 'export_allowed': False}))
        s.commit()
    return source.id

def run(folder, actor='market-curator', dry_run=False, storage=None, database_url=None):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    exported = datetime.fromisoformat(manifest['created_utc'].replace('Z', '+00:00'))
    work, skipped = [], []
    for job in manifest['jobs']:
        if job.get('status') != 'ok' or not job.get('file'):
            skipped.append({'code': job.get('code'), 'reason': job.get('note') or ('no data file of its own' if job.get('status') == 'ok' else job.get('status'))}); continue
        mapped = plan(job)
        if not mapped:
            skipped.append({'code': job['code'], 'reason': 'not a market series (vendor hint list) or not mapped'}); continue
        instrument, fields, price_type, extra = mapped
        path = folder / job['file'].replace('.csv', '.raw.json')
        work.append((job, path, instrument, settings(job, response_columns(path), fields, price_type, extra, instrument, manifest['created_utc'])))
    summary = {'export': str(folder), 'exported_at': manifest['created_utc'], 'series': len(work), 'skipped': skipped,
               'instruments': sorted({instrument['code'] for _, _, instrument, _ in work})}
    if dry_run: return summary
    storage = storage or os.getenv('SNAPSHOT_DIR', 'data/snapshots')
    url = database_url or DATABASE_URL
    with Session(make_engine(url)) as s: source_id = ensure_source(s, actor)
    totals = {'documents': 0, 'duplicate_documents': 0, 'builds': 0, 'observations': 0, 'instruments_created': 0}
    for job, path, instrument, spec in work:
        result = market_import.run(path, source_id, 'lseg:' + job['code'], f"LSEG {job['code']} daily ({instrument['name']}), raw historical-pricing response",
                                   spec, [instrument], exported.date(), actor, storage, url, with_quality=False)
        totals['documents'] += not result['duplicate_document']; totals['duplicate_documents'] += result['duplicate_document']
        totals['builds'] += not result['duplicate_build']; totals['instruments_created'] += len(result['instruments_created'])
        totals['observations'] += 0 if result['duplicate_build'] else result['observations']
    with Session(make_engine(url)) as s: quality = inspect_market_quality(s, storage)
    return {**summary, 'source_id': source_id, **totals,
            'quality': {'status': quality['status'], 'counts': quality['counts'], 'coverage': quality['coverage'],
                        'findings': sorted({(f['code'], f['severity']) for f in quality['findings']})}}

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--dry-run', action='store_true', help='show what would be loaded; write nothing')
    parser.add_argument('--actor', default=os.getenv('WRITE_ACTOR', 'market-curator'))
    args = parser.parse_args()
    print(json.dumps(run(args.folder, args.actor, args.dry_run), indent=2, default=list))

if __name__ == '__main__': main()

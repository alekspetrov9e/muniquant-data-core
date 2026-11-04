"""Record curator status decisions for market data from a list kept in tools/curated/.

Each entry names one series (instrument, price type and, where two deliveries give the same series, the vendor
series) and the dates whose data status the curator decided, with the reason. The list holds no data values. The
observations and their builds stay as delivered; the decision is recorded next to them and audited.

    python -m tools.market_status LIST.json [--dry-run] [--actor NAME]

Uses DATABASE_URL. --dry-run matches every entry and writes nothing; a date without an observation stops the run.
Repeat runs add nothing.
"""
import argparse
import json
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.db import DATABASE_URL, make_engine
from app.market import correct_status
from app.schemas import StatusCorrectionIn

def run(decisions, actor='market-curator', dry_run=False, database_url=None):
    items = [StatusCorrectionIn.model_validate(item) for item in decisions['corrections']]
    with Session(make_engine(database_url or DATABASE_URL)) as s:
        results = [correct_status(s, item, actor) for item in items]
        if dry_run: s.rollback()
        else: s.commit()
    return {'list': decisions['name'], 'dry_run': dry_run,
            'series': [{key: result[key] for key in ('instrument', 'price_type', 'matched', 'corrected')} for result in results]}

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('decisions', type=Path)
    parser.add_argument('--dry-run', action='store_true', help='match every entry; write nothing')
    parser.add_argument('--actor', default=os.getenv('WRITE_ACTOR', 'market-curator'))
    args = parser.parse_args()
    print(json.dumps(run(json.loads(args.decisions.read_text()), args.actor, args.dry_run), indent=2))

if __name__ == '__main__': main()

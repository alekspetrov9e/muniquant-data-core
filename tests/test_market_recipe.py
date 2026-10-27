"""tools/market_recipe.py: a recipe loads a vendor delivery, stores companions, and repeats add nothing. Synthetic files."""
import json
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Document, SourceAccess
from tools import market_recipe
from tests.test_market import SCREEN, SCREEN_SPEC, LME

RECIPE = {'name': 'Synthetic delivery', 'instruments': LME,
          'source': {'name': 'Synthetic vendor screens', 'publisher': 'Test vendor', 'source_type': 'commercial', 'url': 'https://example.org/vendor', 'notes': 'Synthetic',
                     'access': {'export_allowed': False, 'basis': 'Synthetic licence for tests', 'retention': 'Test only'}},
          'imports': [{'file': 'raw/table.tsv', 'locator': 'vendor:table', 'title': 'Synthetic table', 'published_at': '2026-10-27', 'settings': SCREEN_SPEC}],
          'companions': [{'file': 'raw/other.tsv', 'locator': 'vendor:other', 'title': 'Synthetic companion', 'published_at': '2026-10-27'}],
          'left_out': [{'series': 'X', 'reason': 'synthetic'}]}

def test_recipe_loads_once_and_keeps_the_source_internal(client, tmp_path):
    (tmp_path / 'raw').mkdir()
    (tmp_path / 'raw' / 'table.tsv').write_text(SCREEN); (tmp_path / 'raw' / 'other.tsv').write_text('synthetic companion\n')
    url, storage = client.app.state.engine.url.render_as_string(hide_password=False), client.app.state.storage
    first = market_recipe.run(RECIPE, tmp_path, storage=storage, database_url=url)
    assert (first['documents'], first['builds'], first['observations'], first['instruments_created']) == (2, 1, 2, ['LME_AL_CASH', 'LME_AL_3M'])
    again = market_recipe.run(RECIPE, tmp_path, storage=storage, database_url=url)
    assert (again['documents'], again['builds'], again['observations'], again['instruments_created']) == (0, 0, 0, [])
    with Session(client.app.state.engine) as s:
        assert s.scalar(select(SourceAccess).where(SourceAccess.source_id == first['source_id'])).export_allowed is False
        assert s.scalar(select(Document).where(Document.original_url == 'vendor:other')).media_type == 'text/tab-separated-values'
    (tmp_path / 'raw' / 'other.tsv').unlink()
    with pytest.raises(ValueError, match='Missing file'): market_recipe.run(RECIPE, tmp_path, storage=storage, database_url=url)

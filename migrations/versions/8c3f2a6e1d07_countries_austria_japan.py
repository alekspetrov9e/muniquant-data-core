"""Controlled country registry: add Austria and Japan.

Owners of Canadian smelters are registered there (DC2 curation, 2026-10-26). Adding a country is a
governed reference change, so it is a migration; existing rows are untouched.
"""
from alembic import op
import sqlalchemy as sa

revision = '8c3f2a6e1d07'
down_revision = '5b1e0c7d9a42'
branch_labels = None
depends_on = None

COUNTRIES = {'AT': 'Austria', 'JP': 'Japan'}

def upgrade():
    country = sa.table('country', sa.column('code', sa.String), sa.column('name', sa.String))
    op.bulk_insert(country, [{'code': code, 'name': name} for code, name in COUNTRIES.items()])

def downgrade():
    op.execute("DELETE FROM country WHERE code IN ('AT', 'JP')")

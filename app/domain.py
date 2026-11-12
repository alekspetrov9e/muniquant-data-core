# Copyright 2026 muniQuant. Licensed under the Apache License, Version 2.0.
"""Controlled master data, audited aliases and immutable supersession."""
import unicodedata
from sqlalchemy import select, text, update
from .models import Country, Commodity, FacilityType, Region, Company, Facility, EntityAlias, EntitySupersession, Entity

COUNTRIES = dict(AU='Australia', NO='Norway', IS='Iceland', CA='Canada', US='United States', BR='Brazil', QA='Qatar', SK='Slovakia', DE='Germany', FR='France', IN='India', CN='China', RU='Russia', AE='United Arab Emirates', BH='Bahrain', NZ='New Zealand', GB='United Kingdom', ZA='South Africa', JM='Jamaica', GN='Guinea', IE='Ireland', ES='Spain', GR='Greece', MZ='Mozambique', ID='Indonesia', MY='Malaysia', OM='Oman', SA='Saudi Arabia', AT='Austria', JP='Japan')
TYPES = {'smelter':'Primary aluminium smelter', 'refinery':'Alumina refinery', 'bauxite_mine':'Bauxite mine'}
PRODUCTS = {'aluminium':'Aluminium', 'alumina':'Alumina', 'bauxite':'Bauxite'}

def canonical(name):
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in unicodedata.normalize('NFKC', name).casefold()).split())

# The C++ name_distance compares at most 256 code points. Normalisation can expand a name (U+FDFA becomes 18).
NAME_LIMIT = 256

def check_name(name):
    if len(canonical(name)) > NAME_LIMIT: raise ValueError(f'Name is longer than {NAME_LIMIT} characters after Unicode normalisation')

def seed_references(s):
    for model, values in [(Country, COUNTRIES), (FacilityType, TYPES), (Commodity, PRODUCTS)]:
        for code,name in values.items():
            if not s.get(model,code): s.add(model(code=code,name=name))
    s.flush()

def sync_entity(s, entity, actor='migration'):
    check_name(entity.name)
    if not s.get(Country, entity.country): raise ValueError('Country is not in the controlled registry')
    if not s.get(Commodity, entity.commodity): raise ValueError('Unknown commodity')
    if entity.kind == 'company':
        if not s.get(Company,entity.id): s.add(Company(entity_id=entity.id))
    else:
        if not s.get(FacilityType,entity.facility_type): raise ValueError('Unknown facility type')
        region = None
        if entity.region:
            region=s.scalar(select(Region).where(Region.country_code==entity.country,Region.name==entity.region))
            if not region:
                region=Region(country_code=entity.country,name=entity.region); s.add(region); s.flush()
        if not s.get(Facility,entity.id):
            s.add(Facility(entity_id=entity.id,type_code=entity.facility_type,country_code=entity.country,
                           region_id=region.id if region else None,commodity_code=entity.commodity))
    for name in entity.aliases:
        add_alias(s,entity.id,name,actor,'Initial curated alias')
    s.flush()

def lock_entity(s,entity_id):
    """Hold the entity's write lock until commit (its row on PostgreSQL, the database on SQLite), so the reads after it see every earlier write."""
    s.execute(update(Entity).where(Entity.id==entity_id).values(kind=Entity.kind).execution_options(synchronize_session=False))

def add_alias(s,entity_id,name,actor,reason):
    key=canonical(name)
    if not key: raise ValueError('Alias must contain letters or numbers')
    check_name(name)
    # Lock, then read the list, so parallel aliases each extend the latest one.
    lock_entity(s,entity_id)
    entity=s.get(Entity,entity_id,populate_existing=True)
    if not entity: raise ValueError('Unknown entity')
    existing=s.scalar(select(EntityAlias).where(EntityAlias.entity_id==entity_id,EntityAlias.normalized_name==key))
    alias=existing or EntityAlias(entity_id=entity_id,name=name,normalized_name=key,actor=actor,reason=reason)
    s.add(alias)
    # Also lists again an alias recorded earlier but missing from the list.
    if not any(canonical(listed)==key for listed in entity.aliases): entity.aliases=[*entity.aliases,alias.name]
    s.flush(); return alias

def supersede(s,old,new,actor,reason):
    a,b=s.get(Entity,old),s.get(Entity,new)
    if not a or not b or a.kind!=b.kind: raise ValueError('Supersession requires existing entities of the same kind')
    # One supersession at a time, so two in parallel cannot close a loop: lock the whole table on
    # PostgreSQL (a loop can pass through other entities); any write locks the database on SQLite.
    if s.get_bind().dialect.name=='postgresql': s.execute(text('LOCK TABLE entity_supersession IN SHARE ROW EXCLUSIVE MODE'))
    else: lock_entity(s,old)
    cursor=new; visited={old}
    while cursor:
        if cursor in visited: raise ValueError('Supersession cycle')
        visited.add(cursor); link=s.get(EntitySupersession,cursor); cursor=link.new_entity_id if link else None
    if s.get(EntitySupersession,old): raise ValueError('Entity already superseded')
    link=EntitySupersession(old_entity_id=old,new_entity_id=new,actor=actor,reason=reason);s.add(link);s.flush();return link

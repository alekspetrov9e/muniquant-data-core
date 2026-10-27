from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, JSON, CheckConstraint, UniqueConstraint, Boolean, true
from sqlalchemy.orm import declarative_base

Base = declarative_base()
def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc).isoformat()

class Entity(Base):
    __tablename__ = "entities"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String(256), nullable=False)
    kind = Column(String, nullable=False)
    facility_type = Column(String)
    country = Column(String(2))
    region = Column(String)
    commodity = Column(String, nullable=False, default="aluminium")
    aliases = Column(JSON, nullable=False, default=list)
    __table_args__ = (CheckConstraint("kind IN ('company','facility')"),)

class Source(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)
    publisher = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    url = Column(String, nullable=False)
    access_status = Column(String, nullable=False)
    notes = Column(Text, nullable=False, default="")

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=uid)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    original_url = Column(String, nullable=False)
    published_at = Column(String)
    retrieved_at = Column(String, nullable=False, default=now)
    media_type = Column(String, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("source_id", "original_url", "content_hash"),
                      UniqueConstraint("source_id", "original_url", "version"), CheckConstraint("version > 0"))

class Observation(Base):
    __tablename__ = "observations"
    id = Column(String, primary_key=True, default=uid)
    entity_id = Column(String, ForeignKey("entities.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    attribute = Column(String, nullable=False)
    reported_value = Column(String, nullable=False)
    reported_unit = Column(String, nullable=False)
    normalized_value = Column(Float)
    normalized_unit = Column(String)
    valid_from = Column(String, nullable=False)
    valid_to = Column(String)
    evidence_reference = Column(String, nullable=False)
    quality_status = Column(String, nullable=False)
    quality_messages = Column(JSON, nullable=False, default=list)
    parser_version = Column(String, nullable=False, default="manual-v1")
    recorded_at = Column(String, nullable=False, default=now)
    __table_args__ = (CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_observation_interval"),
                      CheckConstraint("normalized_value IS NULL OR normalized_value >= 0", name="ck_observation_nonnegative"),
                      CheckConstraint("(attribute='capacity' AND reported_unit IN ('t/year','kt/year','Mt/year')) OR (attribute='power' AND reported_unit='MW') OR (attribute='ownership_percentage' AND reported_unit='percentage') OR (attribute='status' AND reported_unit='status')", name='ck_observation_dimension'))

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(String, primary_key=True, default=uid)
    company_id = Column(String, ForeignKey("entities.id"), nullable=False)
    facility_id = Column(String, ForeignKey("entities.id"), nullable=False)
    role = Column(String, nullable=False)
    percentage = Column(Float)
    valid_from = Column(String, nullable=False)
    valid_to = Column(String)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    __table_args__ = (CheckConstraint("role IN ('OWNS','OPERATES')"),
                      CheckConstraint("percentage IS NULL OR (CAST(percentage AS NUMERIC) >= 0 AND CAST(percentage AS NUMERIC) <= 100)"),
                      CheckConstraint("valid_to IS NULL OR valid_to >= valid_from"))

class Review(Base):
    __tablename__ = "reviews"
    id = Column(String, primary_key=True, default=uid)
    raw_name = Column(String, nullable=False)
    candidate_ids = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    selected_entity_id = Column(String, ForeignKey("entities.id"))
    reviewer = Column(String)
    reason = Column(Text)
    decided_at = Column(String)

class Run(Base):
    __tablename__ = "runs"
    id = Column(String, primary_key=True, default=uid)
    started_at = Column(String, nullable=False, default=now)
    pipeline_version = Column(String, nullable=False, default="0.1.0")
    status = Column(String, nullable=False)
    manifest = Column(JSON, nullable=False)

class Audit(Base):
    __tablename__ = "audit"
    id = Column(String, primary_key=True, default=uid)
    created_at = Column(String, nullable=False, default=now)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    detail = Column(JSON, nullable=False)

# Controlled reference and provenance records; legacy IDs remain stable.
class Country(Base):
    __tablename__ = 'country'
    code = Column(String(2), primary_key=True)
    name = Column(String, nullable=False)

class Region(Base):
    __tablename__ = 'region'
    id = Column(String, primary_key=True, default=uid)
    country_code = Column(String(2), ForeignKey('country.code'), nullable=False)
    name = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint('country_code', 'name'),)

class FacilityType(Base):
    __tablename__ = 'facility_type'
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class Commodity(Base):
    __tablename__ = 'commodity'
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class Company(Base):
    __tablename__ = 'company'
    entity_id = Column(String, ForeignKey('entities.id'), primary_key=True)

class Facility(Base):
    __tablename__ = 'facility'
    entity_id = Column(String, ForeignKey('entities.id'), primary_key=True)
    type_code = Column(String, ForeignKey('facility_type.code'), nullable=False)
    country_code = Column(String(2), ForeignKey('country.code'), nullable=False)
    region_id = Column(String, ForeignKey('region.id'))
    commodity_code = Column(String, ForeignKey('commodity.code'), nullable=False)

class EntityAlias(Base):
    __tablename__ = 'entity_alias'
    id = Column(String, primary_key=True, default=uid)
    entity_id = Column(String, ForeignKey('entities.id'), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    normalized_name = Column(String(256), nullable=False, index=True)
    actor = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=now)
    __table_args__ = (UniqueConstraint('entity_id', 'normalized_name'),)

class EntitySupersession(Base):
    __tablename__ = 'entity_supersession'
    old_entity_id = Column(String, ForeignKey('entities.id'), primary_key=True)
    new_entity_id = Column(String, ForeignKey('entities.id'), nullable=False)
    actor = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=now)
    __table_args__ = (CheckConstraint('old_entity_id <> new_entity_id', name='ck_supersession_distinct'),)

class SourceAccess(Base):
    __tablename__ = 'source_access'
    id = Column(String, primary_key=True, default=uid)
    source_id = Column(String, ForeignKey('sources.id'), nullable=False, index=True)
    status = Column(String, nullable=False)
    allowed_hosts = Column(JSON, nullable=False)
    basis = Column(Text, nullable=False)
    retention = Column(Text, nullable=False)
    reviewer = Column(String, nullable=False)
    decided_at = Column(String, nullable=False, default=now)
    # Name of the server environment variable holding an API credential; never the secret itself.
    credential_ref = Column(String(64))
    auth_header = Column(String(64))
    # Whether data from this source may leave the Core in an export; licensed data can be internal only.
    export_allowed = Column(Boolean, nullable=False, default=True, server_default=true())
    __table_args__ = (CheckConstraint("status IN ('permitted','review_required','restricted')", name='ck_source_access_status'),
                      CheckConstraint('(credential_ref IS NULL) = (auth_header IS NULL)', name='ck_source_access_credential'))

class SourceSnapshot(Base):
    __tablename__ = 'source_snapshot'
    content_hash = Column(String(64), primary_key=True)
    storage_reference = Column(String, nullable=False)
    byte_size = Column(Integer)
    __table_args__ = (CheckConstraint('byte_size >= 0', name='ck_snapshot_size'),)

class DocumentVersion(Base):
    __tablename__ = 'document_version'
    document_id = Column(String, ForeignKey('documents.id'), primary_key=True)
    snapshot_hash = Column(String(64), ForeignKey('source_snapshot.content_hash'), nullable=False)
    version = Column(Integer, nullable=False)
    __table_args__ = (CheckConstraint('version > 0', name='ck_document_version_positive'),)

class SourceDocumentRelation(Base):
    __tablename__ = 'source_document_relation'
    source_id = Column(String, ForeignKey('sources.id'), primary_key=True)
    document_id = Column(String, ForeignKey('documents.id'), primary_key=True)

class RetrievalAttempt(Base):
    __tablename__ = 'retrieval_attempt'
    id = Column(String, primary_key=True, default=uid)
    run_id = Column(String, ForeignKey('runs.id'), nullable=False, index=True)
    url = Column(String, nullable=False)
    attempt = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    error = Column(String)
    http_status = Column(Integer)
    recorded_at = Column(String, nullable=False, default=now)

class EvidenceBuild(Base):
    __tablename__ = 'evidence_build'
    id = Column(String(64), primary_key=True)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False)
    content_hash = Column(String(64), nullable=False)
    parser_version = Column(String, nullable=False)
    pipeline_version = Column(String, nullable=False)
    specification = Column(JSON, nullable=False)
    logical_output = Column(JSON, nullable=False)
    output_hash = Column(String(64), nullable=False)
    actor = Column(String, nullable=False)
    created_at = Column(String, nullable=False, default=now)

class Candidate(Base):
    __tablename__ = 'candidate'
    id = Column(String, primary_key=True)
    build_id = Column(String, ForeignKey('evidence_build.id'), nullable=False, index=True)
    raw_name = Column(String, nullable=False)
    country = Column(String(2))
    reported_value = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    evidence_reference = Column(String, nullable=False)
    status = Column(String, nullable=False)
    entity_id = Column(String, ForeignKey('entities.id'))
    observation_id = Column(String, ForeignKey('observations.id'))
    review_id = Column(String, ForeignKey('reviews.id'))
    findings = Column(JSON, nullable=False, default=list)

from sqlalchemy import Date, Numeric
from sqlalchemy.types import TypeDecorator
from decimal import Decimal

class ExactDecimal(TypeDecorator):
    impl = Numeric(30, 6)
    cache_ok = True
    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(String(40) if dialect.name == 'sqlite' else Numeric(30, 6))
    def process_bind_param(self, value, dialect):
        if value is None: return None
        return format(Decimal(value), 'f') if dialect.name == 'sqlite' else Decimal(value)
    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None

class ObservationDetail(Base):
    __tablename__ = 'observation_detail'
    observation_id = Column(String, ForeignKey('observations.id'), primary_key=True)
    normalized_value = Column(ExactDecimal())
    normalized_unit = Column(String)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date)
    __table_args__ = (
        CheckConstraint('normalized_value IS NULL OR normalized_value >= 0', name='ck_detail_nonnegative'),
        CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='ck_detail_interval'),
        CheckConstraint("normalized_unit IS NULL OR normalized_unit IN ('t/year','MW','percentage')", name='ck_detail_unit'),
    )

class CompanyFacilityRelationship(Base):
    __tablename__ = 'company_facility_relationship'
    relationship_id = Column(String, ForeignKey('relationships.id'), primary_key=True)
    company_id = Column(String, ForeignKey('company.entity_id'), nullable=False)
    facility_id = Column(String, ForeignKey('facility.entity_id'), nullable=False)
    document_id = Column(String, ForeignKey('document_version.document_id'), nullable=False)
    role = Column(String, nullable=False)
    percentage = Column(ExactDecimal())
    evidence_reference = Column(Text, nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date)
    __table_args__ = (CheckConstraint("role IN ('OWNS','OPERATES')", name='ck_relationship_role'),
                     CheckConstraint('percentage IS NULL OR (CAST(percentage AS NUMERIC) >= 0 AND CAST(percentage AS NUMERIC) <= 100)', name='ck_relationship_share'),
                     CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='ck_relationship_interval'))

class EntityEvidence(Base):
    __tablename__ = 'entity_evidence'
    entity_id = Column(String, ForeignKey('entities.id'), primary_key=True)
    document_id = Column(String, ForeignKey('document_version.document_id'), primary_key=True)
    evidence_reference = Column(Text, nullable=False)
    reviewer = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=now)

# Market data area (added after DC1, approved 2026-10-26): instruments and their observations.
# Each observation comes from one registered document version through one replayable build.
PRICE_UNITS = {'USD/t': 'USD', 'USc/lb': 'USD', 'USD/lb': 'USD', 'CNY/t': 'CNY', 'EUR/t': 'EUR', 'JPY/t': 'JPY'}
PRICE_TYPES = ('official', 'closing', 'settlement', 'daily', 'assessment', 'intraday')
PRICE_FIELDS = ('bid', 'ask', 'open', 'high', 'low', 'close', 'settlement')
QUANTITY_FIELDS = ('volume', 'open_interest')
DATA_STATUSES = ('reported', 'provisional', 'final', 'carried_forward', 'corrected')

class Instrument(Base):
    __tablename__ = 'market_instrument'
    id = Column(String, primary_key=True, default=uid)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(256), nullable=False)
    exchange = Column(String(16))
    market = Column(String(16), nullable=False)
    commodity = Column(String, ForeignKey('commodity.code'), nullable=False)
    grade = Column(String(256))
    region = Column(String(128))
    # A rolling point (cash, 3M, front, active...) or one dated contract, never both.
    tenor = Column(String(32))
    contract_code = Column(String(32))
    contract_month = Column(String(7))
    currency = Column(String(3), nullable=False)
    unit = Column(String(16), nullable=False)
    quantity_unit = Column(String(16))
    description = Column(Text, nullable=False, default='')
    created_at = Column(String, nullable=False, default=now)
    __table_args__ = (CheckConstraint("market IN ('forward','futures','physical')", name='ck_instrument_market'),
                      CheckConstraint("market = 'physical' OR exchange IS NOT NULL", name='ck_instrument_exchange'),
                      CheckConstraint("market <> 'forward' OR tenor IS NOT NULL", name='ck_instrument_forward_tenor'),
                      CheckConstraint('tenor IS NULL OR contract_month IS NULL', name='ck_instrument_point_or_contract'),
                      CheckConstraint('(contract_code IS NULL) = (contract_month IS NULL)', name='ck_instrument_contract'),
                      CheckConstraint("unit IN ('USD/t','USc/lb','USD/lb','CNY/t','EUR/t','JPY/t')", name='ck_instrument_unit'),
                      CheckConstraint("quantity_unit IS NULL OR quantity_unit IN ('lots','contracts','t')", name='ck_instrument_quantity_unit'))

class MarketBuild(Base):
    __tablename__ = 'market_build'
    id = Column(String(64), primary_key=True)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    parser_version = Column(String, nullable=False)
    pipeline_version = Column(String, nullable=False)
    specification = Column(JSON, nullable=False)
    logical_output = Column(JSON, nullable=False)
    output_hash = Column(String(64), nullable=False)
    actor = Column(String, nullable=False)
    created_at = Column(String, nullable=False, default=now)

def _amount(name): return f'CAST({name} AS NUMERIC)'

class InstrumentObservation(Base):
    __tablename__ = 'market_observation'
    id = Column(String, primary_key=True)
    instrument_id = Column(String, ForeignKey('market_instrument.id'), nullable=False, index=True)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False, index=True)
    build_id = Column(String(64), ForeignKey('market_build.id'), nullable=False, index=True)
    price_type = Column(String(16), nullable=False)
    # Trading or assessment date; effective_at is the exact UTC instant when the source gives one.
    effective_date = Column(Date, nullable=False)
    effective_at = Column(String(32))
    contract_code = Column(String(32))
    contract_month = Column(String(7))
    prompt_date = Column(Date)
    bid = Column(ExactDecimal())
    ask = Column(ExactDecimal())
    open = Column(ExactDecimal())
    high = Column(ExactDecimal())
    low = Column(ExactDecimal())
    close = Column(ExactDecimal())
    settlement = Column(ExactDecimal())
    volume = Column(ExactDecimal())
    open_interest = Column(ExactDecimal())
    published_at = Column(String(32))
    retrieved_at = Column(String(32), nullable=False)
    data_status = Column(String(16), nullable=False)
    source_series = Column(JSON, nullable=False, default=dict)
    evidence_reference = Column(Text, nullable=False)
    recorded_at = Column(String, nullable=False, default=now)
    __table_args__ = (CheckConstraint("price_type IN ('official','closing','settlement','daily','assessment','intraday')", name='ck_market_price_type'),
                      CheckConstraint("data_status IN ('reported','provisional','final','carried_forward','corrected')", name='ck_market_data_status'),
                      CheckConstraint(' OR '.join(f'{name} IS NOT NULL' for name in (*PRICE_FIELDS, *QUANTITY_FIELDS)), name='ck_market_has_value'),
                      CheckConstraint(f"high IS NULL OR low IS NULL OR {_amount('high')} >= {_amount('low')}", name='ck_market_high_low'),
                      CheckConstraint(f"bid IS NULL OR ask IS NULL OR {_amount('bid')} <= {_amount('ask')}", name='ck_market_bid_ask'),
                      CheckConstraint(f"volume IS NULL OR {_amount('volume')} >= 0", name='ck_market_volume'),
                      CheckConstraint(f"open_interest IS NULL OR {_amount('open_interest')} >= 0", name='ck_market_open_interest'))

BEGIN TRANSACTION;
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO "alembic_version" VALUES('fcf5b3d9e812');
CREATE TABLE audit (
	id VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	actor VARCHAR NOT NULL, 
	action VARCHAR NOT NULL, 
	record_id VARCHAR NOT NULL, 
	detail JSON NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "audit" VALUES('1bf6277f-6925-41c7-9ac2-5a7725d7d814','2026-10-13T17:37:40.181138+00:00','fixture-pilot-curator','extract_observation','667a6b09-0f70-4cc8-a939-0842e20cece6','{"build_id": "994dc789e73eaaa8119c1857ca6db1b16ead7d0dddff4661a86ef93686112999", "candidate_id": "fe5049ec-149f-51bf-b547-153feaf5088b"}');
INSERT INTO "audit" VALUES('5cff6fc1-9eba-4efa-942e-6529d1ba764f','2026-10-13T17:37:40.183632+00:00','fixture-pilot-curator','extract_observation','f619bb57-428c-4815-b2ee-68522e9caa6e','{"build_id": "edb974344f1a272f0b758203a0c63050c5d3275555b4e7c910c9628d9d925ccd", "candidate_id": "8f739d4e-3660-5a8d-9d78-d1441c1d6dee"}');
INSERT INTO "audit" VALUES('6c98ac12-c57f-423b-9475-07530661abe7','2026-10-13T17:37:40.186373+00:00','fixture-pilot-curator','extract_observation','c8cad943-034e-41d9-9ae5-f98d4c90d1aa','{"build_id": "050de9d997d81225d15a43eb165bd741636d832c5fa0f7dcecf970bb4a7e8b7a", "candidate_id": "c40b71b1-573c-588e-9f5d-6ec53eff1fda"}');
INSERT INTO "audit" VALUES('2e0c3d7e-a9d1-41fb-9acf-92a9e667b90c','2026-10-13T17:37:40.188265+00:00','fixture-pilot-curator','extract_observation','2376e8c7-fc60-4bd4-99d8-5f040c587622','{"build_id": "e707cfcde303beb4146f29a501eaaf9482deb407ff5cb519e0726b2b80bcd01a", "candidate_id": "ed6da5eb-5f32-5ebf-b55c-4f77ecc3d9e2"}');
INSERT INTO "audit" VALUES('47ac8aab-d3ac-49f3-909d-9156a8b72d8b','2026-10-13T17:37:40.191110+00:00','fixture-pilot-curator','curated_relationship','2e693cb9-ffb0-5f48-8d5f-bc0e92b5cedc','{"source": "Fixture fact sheet page 1", "as_of_policy": "snapshot observation date, not historical change date"}');
INSERT INTO "audit" VALUES('0e8ae5c0-21c3-4b7f-ab2e-a069364b6ef0','2026-10-13T17:37:40.191767+00:00','fixture-pilot-curator','curated_relationship','9090d0d2-dd8b-5060-b255-df20b2c1a065','{"source": "Fixture fact sheet page 1", "as_of_policy": "snapshot observation date, not historical change date"}');
INSERT INTO "audit" VALUES('8868840b-6f65-4ca1-b9f4-3484e13d820f','2026-10-13T17:37:40.192077+00:00','fixture-pilot-curator','curated_relationship','c5b5e5b9-d92a-55da-829d-d990bc829715','{"source": "Fixture fact sheet page 1", "as_of_policy": "snapshot observation date, not historical change date"}');
INSERT INTO "audit" VALUES('d1966927-68d6-421c-873a-9093b34771a4','2026-10-13T17:37:40.192256+00:00','fixture-pilot-curator','curated_relationship','8b8b76b5-f09a-5807-ac0e-34a090dc6efb','{"source": "Fixture fact sheet page 1", "as_of_policy": "snapshot observation date, not historical change date"}');
INSERT INTO "audit" VALUES('d9c24b13-b8bb-46c1-843a-31236f531e1b','2026-10-13T17:37:40.217269+00:00','local-curator','review_observation','d8800ba9-e1f7-47a1-8a3a-f9aee71ecc02','{"review_id": "faccc0aa-c140-425d-bcd0-017012d5c9ae", "candidate_id": "72e336be-a000-50c6-901d-5c4694d40d3c"}');
INSERT INTO "audit" VALUES('24e0d845-1af0-4e66-93ac-cee6fe151beb','2026-10-13T17:37:40.217409+00:00','local-curator','review_decision','faccc0aa-c140-425d-bcd0-017012d5c9ae','{"type": "reviews"}');
INSERT INTO "audit" VALUES('7833cac2-fd7a-4d1c-b5f4-1d00e5ebbccb','2026-10-13T17:37:40.220527+00:00','local-curator','review_decision','bf4ca449-62ae-48f9-b72d-1f9a7fa0df71','{"type": "reviews"}');
INSERT INTO "audit" VALUES('5c47b211-7ee6-4e27-a3ac-5691e757cdd9','2026-10-13T17:37:40.222793+00:00','local-curator','observe','12424ff2-2a05-4326-ae89-2a9baf3ac983','{"type": "observations"}');
CREATE TABLE candidate (
	id VARCHAR NOT NULL, 
	build_id VARCHAR NOT NULL, 
	raw_name VARCHAR NOT NULL, 
	country VARCHAR(2), 
	reported_value VARCHAR NOT NULL, 
	unit VARCHAR NOT NULL, 
	evidence_reference VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	entity_id VARCHAR, 
	observation_id VARCHAR, 
	review_id VARCHAR, 
	findings JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(build_id) REFERENCES evidence_build (id), 
	FOREIGN KEY(entity_id) REFERENCES entities (id), 
	FOREIGN KEY(observation_id) REFERENCES observations (id), 
	FOREIGN KEY(review_id) REFERENCES reviews (id)
);
INSERT INTO "candidate" VALUES('fe5049ec-149f-51bf-b547-153feaf5088b','994dc789e73eaaa8119c1857ca6db1b16ead7d0dddff4661a86ef93686112999','North Fjord Works','NO','197,000','t/year','HTML text, text offset 112; context: annual production capacity of 197,000 tonnes of primary aluminium','resolved','9fbc621b-31df-5ad7-bd98-91e8864de4cd','667a6b09-0f70-4cc8-a939-0842e20cece6',NULL,'[]');
INSERT INTO "candidate" VALUES('8f739d4e-3660-5a8d-9d78-d1441c1d6dee','edb974344f1a272f0b758203a0c63050c5d3275555b4e7c910c9628d9d925ccd','North Fjord Works','NO','205,000','t/year','HTML text, text offset 112; context: annual production capacity of 205,000 tonnes of primary aluminium','resolved','9fbc621b-31df-5ad7-bd98-91e8864de4cd','f619bb57-428c-4815-b2ee-68522e9caa6e',NULL,'[]');
INSERT INTO "candidate" VALUES('c40b71b1-573c-588e-9f5d-6ec53eff1fda','050de9d997d81225d15a43eb165bd741636d832c5fa0f7dcecf970bb4a7e8b7a','South Bay Smelter','AU','358,000','t/year','PDF page 1, text offset 133; context: annual nameplate production capacity of 358,000 metric tons','resolved','1af30f84-960f-593d-86e2-2c0193765c6c','c8cad943-034e-41d9-9ae5-f98d4c90d1aa',NULL,'[]');
INSERT INTO "candidate" VALUES('ed6da5eb-5f32-5ebf-b55c-4f77ecc3d9e2','e707cfcde303beb4146f29a501eaaf9482deb407ff5cb519e0726b2b80bcd01a','East Ridge Refinery','AU','1.4','Mt/year','CSV row 2: synthetic test fixture register row East Ridge Refinery','resolved','367f7d1a-2e74-5c27-afe0-490d9b5035dd','2376e8c7-fc60-4bd4-99d8-5f040c587622',NULL,'[]');
INSERT INTO "candidate" VALUES('72e336be-a000-50c6-901d-5c4694d40d3c','e707cfcde303beb4146f29a501eaaf9482deb407ff5cb519e0726b2b80bcd01a','Ridge Operations','AU','9.5','Mt/year','CSV row 3: synthetic test fixture register row Ridge Operations','resolved','8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','d8800ba9-e1f7-47a1-8a3a-f9aee71ecc02','faccc0aa-c140-425d-bcd0-017012d5c9ae','[]');
INSERT INTO "candidate" VALUES('b54c0612-fb87-5c39-bdb7-77d05176d757','e707cfcde303beb4146f29a501eaaf9482deb407ff5cb519e0726b2b80bcd01a','Unknown Lagoon Works','NZ','300','kt/year','CSV row 4: synthetic test fixture register row Unknown Lagoon Works','rejected',NULL,NULL,'bf4ca449-62ae-48f9-b72d-1f9a7fa0df71','[{"code": "UNRESOLVED_ENTITY", "severity": "BLOCK", "message": "Human identity review required"}]');
CREATE TABLE commodity (
	code VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (code)
);
INSERT INTO "commodity" VALUES('aluminium','Aluminium');
INSERT INTO "commodity" VALUES('alumina','Alumina');
INSERT INTO "commodity" VALUES('bauxite','Bauxite');
CREATE TABLE company (
	entity_id VARCHAR NOT NULL, 
	PRIMARY KEY (entity_id), 
	FOREIGN KEY(entity_id) REFERENCES entities (id)
);
INSERT INTO "company" VALUES('c2a6ea61-0113-5f68-82ce-dbc98fc923e3');
INSERT INTO "company" VALUES('40af3bb6-64f3-532d-a67e-21df04b9cf73');
INSERT INTO "company" VALUES('a96327dc-a6ee-5d81-bb02-d55a816c3fec');
INSERT INTO "company" VALUES('0f4617a1-d7e0-5a25-9147-9f00ffbe6b3b');
CREATE TABLE "company_facility_relationship" (
	relationship_id VARCHAR NOT NULL, 
	company_id VARCHAR NOT NULL, 
	facility_id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	evidence_reference TEXT NOT NULL, 
	percentage VARCHAR(40), 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	PRIMARY KEY (relationship_id), 
	CONSTRAINT ck_relationship_interval CHECK (valid_to IS NULL OR valid_to >= valid_from), 
	CONSTRAINT ck_relationship_role CHECK (role IN ('OWNS','OPERATES')), 
	CONSTRAINT ck_relationship_share CHECK (percentage IS NULL OR (CAST(percentage AS NUMERIC) >= 0 AND CAST(percentage AS NUMERIC) <= 100)), 
	FOREIGN KEY(document_id) REFERENCES document_version (document_id), 
	FOREIGN KEY(facility_id) REFERENCES facility (entity_id), 
	FOREIGN KEY(company_id) REFERENCES company (entity_id), 
	FOREIGN KEY(relationship_id) REFERENCES relationships (id)
);
INSERT INTO "company_facility_relationship" VALUES('2e693cb9-ffb0-5f48-8d5f-bc0e92b5cedc','40af3bb6-64f3-532d-a67e-21df04b9cf73','1af30f84-960f-593d-86e2-2c0193765c6c','634b38d8-49cf-4188-82bf-bf5c233ba716','OWNS','PDF page 1, Ownership and Operations lines','55','2026-10-10',NULL);
INSERT INTO "company_facility_relationship" VALUES('9090d0d2-dd8b-5060-b255-df20b2c1a065','a96327dc-a6ee-5d81-bb02-d55a816c3fec','1af30f84-960f-593d-86e2-2c0193765c6c','634b38d8-49cf-4188-82bf-bf5c233ba716','OWNS','PDF page 1, Ownership and Operations lines','22.5','2026-10-10',NULL);
INSERT INTO "company_facility_relationship" VALUES('c5b5e5b9-d92a-55da-829d-d990bc829715','0f4617a1-d7e0-5a25-9147-9f00ffbe6b3b','1af30f84-960f-593d-86e2-2c0193765c6c','634b38d8-49cf-4188-82bf-bf5c233ba716','OWNS','PDF page 1, Ownership and Operations lines','22.5','2026-10-10',NULL);
INSERT INTO "company_facility_relationship" VALUES('8b8b76b5-f09a-5807-ac0e-34a090dc6efb','40af3bb6-64f3-532d-a67e-21df04b9cf73','1af30f84-960f-593d-86e2-2c0193765c6c','634b38d8-49cf-4188-82bf-bf5c233ba716','OPERATES','PDF page 1, Ownership and Operations lines',NULL,'2026-10-10',NULL);
CREATE TABLE country (
	code VARCHAR(2) NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (code)
);
INSERT INTO "country" VALUES('AU','Australia');
INSERT INTO "country" VALUES('NO','Norway');
INSERT INTO "country" VALUES('IS','Iceland');
INSERT INTO "country" VALUES('CA','Canada');
INSERT INTO "country" VALUES('US','United States');
INSERT INTO "country" VALUES('BR','Brazil');
INSERT INTO "country" VALUES('QA','Qatar');
INSERT INTO "country" VALUES('SK','Slovakia');
INSERT INTO "country" VALUES('DE','Germany');
INSERT INTO "country" VALUES('FR','France');
INSERT INTO "country" VALUES('IN','India');
INSERT INTO "country" VALUES('CN','China');
INSERT INTO "country" VALUES('RU','Russia');
INSERT INTO "country" VALUES('AE','United Arab Emirates');
INSERT INTO "country" VALUES('BH','Bahrain');
INSERT INTO "country" VALUES('NZ','New Zealand');
INSERT INTO "country" VALUES('GB','United Kingdom');
INSERT INTO "country" VALUES('ZA','South Africa');
INSERT INTO "country" VALUES('JM','Jamaica');
INSERT INTO "country" VALUES('GN','Guinea');
INSERT INTO "country" VALUES('IE','Ireland');
INSERT INTO "country" VALUES('ES','Spain');
INSERT INTO "country" VALUES('GR','Greece');
INSERT INTO "country" VALUES('MZ','Mozambique');
INSERT INTO "country" VALUES('ID','Indonesia');
INSERT INTO "country" VALUES('MY','Malaysia');
INSERT INTO "country" VALUES('OM','Oman');
INSERT INTO "country" VALUES('SA','Saudi Arabia');
CREATE TABLE document_version (
	document_id VARCHAR NOT NULL, 
	snapshot_hash VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (document_id), 
	CONSTRAINT ck_document_version_positive CHECK (version > 0), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(snapshot_hash) REFERENCES source_snapshot (content_hash)
);
INSERT INTO "document_version" VALUES('34fb16bf-dc3a-4cae-8a4e-06433fecf541','25cfb138a1b164c8ce6e4e0aaaa669d83c2566c11f747592e3b676a062b1ff27',1);
INSERT INTO "document_version" VALUES('8f4bba96-4edb-4b6c-972a-7f5db7068367','48badb380aa4ba007433298887f6e956d5dd8b3293922ccaa4ca2fa9dc574165',1);
INSERT INTO "document_version" VALUES('634b38d8-49cf-4188-82bf-bf5c233ba716','a342868ffefabf74e89c2a51ee3c344da564cae8f1344d161d6a9946c0fadff3',1);
INSERT INTO "document_version" VALUES('83ef134f-280a-4b12-a871-240f9b85a48f','868123cfcafa57f8bb7297c1f6c3bc2845e2321ef523daec273197455f1841d2',1);
INSERT INTO "document_version" VALUES('9436874c-1552-4b8f-951e-a413812e2366','18ae6ed358f32caff1637874b92df569e559c73e15970e538e48ba77ad0c308a',2);
CREATE TABLE documents (
	id VARCHAR NOT NULL, 
	source_id VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	original_url VARCHAR NOT NULL, 
	published_at VARCHAR, 
	retrieved_at VARCHAR NOT NULL, 
	media_type VARCHAR NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (version > 0), 
	FOREIGN KEY(source_id) REFERENCES sources (id), 
	UNIQUE (source_id, original_url, content_hash), 
	UNIQUE (source_id, original_url, version)
);
INSERT INTO "documents" VALUES('34fb16bf-dc3a-4cae-8a4e-06433fecf541','caab08c6-7026-5cf4-b602-154cc3cdca33','fjord-v1 fixture evidence','https://example.org/northern/news/fjord-capacity.html','2024-12-19','2026-10-13T17:37:40.155775+00:00','text/html','25cfb138a1b164c8ce6e4e0aaaa669d83c2566c11f747592e3b676a062b1ff27',1);
INSERT INTO "documents" VALUES('8f4bba96-4edb-4b6c-972a-7f5db7068367','caab08c6-7026-5cf4-b602-154cc3cdca33','operations fixture evidence','https://example.org/northern/operations.html',NULL,'2026-10-13T17:37:40.159422+00:00','text/html','48badb380aa4ba007433298887f6e956d5dd8b3293922ccaa4ca2fa9dc574165',1);
INSERT INTO "documents" VALUES('634b38d8-49cf-4188-82bf-bf5c233ba716','ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8','bay fixture evidence','https://example.com/southern/bay-fact-sheet.pdf',NULL,'2026-10-13T17:37:40.162222+00:00','application/pdf','a342868ffefabf74e89c2a51ee3c344da564cae8f1344d161d6a9946c0fadff3',1);
INSERT INTO "documents" VALUES('83ef134f-280a-4b12-a871-240f9b85a48f','ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8','register fixture evidence','https://example.com/southern/register.csv','2025-03-31','2026-10-13T17:37:40.164607+00:00','text/csv','868123cfcafa57f8bb7297c1f6c3bc2845e2321ef523daec273197455f1841d2',1);
INSERT INTO "documents" VALUES('9436874c-1552-4b8f-951e-a413812e2366','caab08c6-7026-5cf4-b602-154cc3cdca33','fjord-v2 fixture evidence','https://example.org/northern/news/fjord-capacity.html','2025-06-30','2026-10-13T17:37:40.166835+00:00','text/html','18ae6ed358f32caff1637874b92df569e559c73e15970e538e48ba77ad0c308a',2);
CREATE TABLE entities (
	id VARCHAR NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	kind VARCHAR NOT NULL, 
	facility_type VARCHAR, 
	country VARCHAR(2), 
	region VARCHAR, 
	commodity VARCHAR NOT NULL, 
	aliases JSON NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (kind IN ('company','facility'))
);
INSERT INTO "entities" VALUES('9fbc621b-31df-5ad7-bd98-91e8864de4cd','North Fjord Works','facility','smelter','NO','','aluminium','[]');
INSERT INTO "entities" VALUES('52dcf50b-4407-50b8-9a18-1748413b3f3a','Harbour Point Smelter','facility','smelter','NO','','aluminium','["Harbour Point"]');
INSERT INTO "entities" VALUES('1af30f84-960f-593d-86e2-2c0193765c6c','South Bay Smelter','facility','smelter','AU','','aluminium','[]');
INSERT INTO "entities" VALUES('367f7d1a-2e74-5c27-afe0-490d9b5035dd','East Ridge Refinery','facility','refinery','AU','','alumina','["East Ridge", "Ridge Operations"]');
INSERT INTO "entities" VALUES('8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','West Ridge Mine','facility','bauxite_mine','AU','','bauxite','["West Ridge", "Ridge Operations"]');
INSERT INTO "entities" VALUES('c2a6ea61-0113-5f68-82ce-dbc98fc923e3','Example Northern Aluminium','company',NULL,'NO','','aluminium','[]');
INSERT INTO "entities" VALUES('40af3bb6-64f3-532d-a67e-21df04b9cf73','Example Southern Smelting','company',NULL,'AU','','aluminium','[]');
INSERT INTO "entities" VALUES('a96327dc-a6ee-5d81-bb02-d55a816c3fec','Example Partner Holdings','company',NULL,'GB','','aluminium','[]');
INSERT INTO "entities" VALUES('0f4617a1-d7e0-5a25-9147-9f00ffbe6b3b','Example Metals Investment','company',NULL,'CN','','aluminium','[]');
CREATE TABLE entity_alias (
	id VARCHAR NOT NULL, 
	entity_id VARCHAR NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	normalized_name VARCHAR(256) NOT NULL, 
	actor VARCHAR NOT NULL, 
	reason TEXT NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(entity_id) REFERENCES entities (id), 
	UNIQUE (entity_id, normalized_name)
);
INSERT INTO "entity_alias" VALUES('8334082d-9fd0-435e-845f-2cf09275094a','52dcf50b-4407-50b8-9a18-1748413b3f3a','Harbour Point','harbour point','fixture-pilot-curator','Initial curated alias','2026-10-13T17:37:40.171354+00:00');
INSERT INTO "entity_alias" VALUES('e64e30a3-e9da-4538-84fd-4b4114b27055','367f7d1a-2e74-5c27-afe0-490d9b5035dd','East Ridge','east ridge','fixture-pilot-curator','Initial curated alias','2026-10-13T17:37:40.172825+00:00');
INSERT INTO "entity_alias" VALUES('e5d8c770-9ebb-4494-8e05-c00ac83ddc3b','367f7d1a-2e74-5c27-afe0-490d9b5035dd','Ridge Operations','ridge operations','fixture-pilot-curator','Initial curated alias','2026-10-13T17:37:40.173008+00:00');
INSERT INTO "entity_alias" VALUES('7b88df54-7fde-4898-b552-f90aa17919a3','8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','West Ridge','west ridge','fixture-pilot-curator','Initial curated alias','2026-10-13T17:37:40.173660+00:00');
INSERT INTO "entity_alias" VALUES('9a50ba4f-b3dc-4f1a-9169-be54fdc82508','8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','Ridge Operations','ridge operations','fixture-pilot-curator','Initial curated alias','2026-10-13T17:37:40.173818+00:00');
CREATE TABLE entity_evidence (
	entity_id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	evidence_reference TEXT NOT NULL, 
	reviewer VARCHAR NOT NULL, 
	reason TEXT NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (entity_id, document_id), 
	FOREIGN KEY(document_id) REFERENCES document_version (document_id), 
	FOREIGN KEY(entity_id) REFERENCES entities (id)
);
INSERT INTO "entity_evidence" VALUES('9fbc621b-31df-5ad7-bd98-91e8864de4cd','34fb16bf-dc3a-4cae-8a4e-06433fecf541','Fixture operations text: North Fjord Works','fixture-pilot-curator','Curated fixture facility name, country and industrial class from the fixture source','2026-10-13T17:37:40.170305+00:00');
INSERT INTO "entity_evidence" VALUES('52dcf50b-4407-50b8-9a18-1748413b3f3a','8f4bba96-4edb-4b6c-972a-7f5db7068367','Fixture operations text: Harbour Point','fixture-pilot-curator','Curated fixture facility name, country and industrial class from the fixture source','2026-10-13T17:37:40.171675+00:00');
INSERT INTO "entity_evidence" VALUES('1af30f84-960f-593d-86e2-2c0193765c6c','634b38d8-49cf-4188-82bf-bf5c233ba716','PDF page 1: SOUTH BAY SMELTER','fixture-pilot-curator','Curated fixture facility name, country and industrial class from the fixture source','2026-10-13T17:37:40.172271+00:00');
INSERT INTO "entity_evidence" VALUES('367f7d1a-2e74-5c27-afe0-490d9b5035dd','8f4bba96-4edb-4b6c-972a-7f5db7068367','Fixture operations text: East Ridge','fixture-pilot-curator','Curated fixture facility name, country and industrial class from the fixture source','2026-10-13T17:37:40.173141+00:00');
INSERT INTO "entity_evidence" VALUES('8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','8f4bba96-4edb-4b6c-972a-7f5db7068367','Fixture operations text: West Ridge','fixture-pilot-curator','Curated fixture facility name, country and industrial class from the fixture source','2026-10-13T17:37:40.173943+00:00');
CREATE TABLE entity_supersession (
	old_entity_id VARCHAR NOT NULL, 
	new_entity_id VARCHAR NOT NULL, 
	actor VARCHAR NOT NULL, 
	reason TEXT NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (old_entity_id), 
	CONSTRAINT ck_supersession_distinct CHECK (old_entity_id <> new_entity_id), 
	FOREIGN KEY(new_entity_id) REFERENCES entities (id), 
	FOREIGN KEY(old_entity_id) REFERENCES entities (id)
);
CREATE TABLE evidence_build (
	id VARCHAR(64) NOT NULL, 
	document_id VARCHAR NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	parser_version VARCHAR NOT NULL, 
	pipeline_version VARCHAR NOT NULL, 
	specification JSON NOT NULL, 
	logical_output JSON NOT NULL, 
	output_hash VARCHAR(64) NOT NULL, 
	actor VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
);
INSERT INTO "evidence_build" VALUES('994dc789e73eaaa8119c1857ca6db1b16ead7d0dddff4661a86ef93686112999','34fb16bf-dc3a-4cae-8a4e-06433fecf541','25cfb138a1b164c8ce6e4e0aaaa669d83c2566c11f747592e3b676a062b1ff27','industrial-adapters-1.0.0','1.0.0','{"adapter": "html-v1", "facility_name": "North Fjord Works", "country": "NO", "valid_from": "2024-12-19", "valid_to": null, "unit": "t/year", "attribute": "capacity", "prefix": "annual production capacity of", "suffix": "tonnes of primary aluminium", "page": null}','[{"facility_name": "North Fjord Works", "country": "NO", "reported_value": "197,000", "unit": "t/year", "valid_from": "2024-12-19", "valid_to": null, "attribute": "capacity", "evidence_reference": "HTML text, text offset 112; context: annual production capacity of 197,000 tonnes of primary aluminium"}]','f3661084900b89cc75bec6bd0bfe50436e4c4ec1b801024aa43e9ac65bf07ffd','fixture-pilot-curator','2026-10-13T17:37:40.177728+00:00');
INSERT INTO "evidence_build" VALUES('edb974344f1a272f0b758203a0c63050c5d3275555b4e7c910c9628d9d925ccd','9436874c-1552-4b8f-951e-a413812e2366','18ae6ed358f32caff1637874b92df569e559c73e15970e538e48ba77ad0c308a','industrial-adapters-1.0.0','1.0.0','{"adapter": "html-v1", "facility_name": "North Fjord Works", "country": "NO", "valid_from": "2025-06-30", "valid_to": null, "unit": "t/year", "attribute": "capacity", "prefix": "annual production capacity of", "suffix": "tonnes of primary aluminium", "page": null}','[{"facility_name": "North Fjord Works", "country": "NO", "reported_value": "205,000", "unit": "t/year", "valid_from": "2025-06-30", "valid_to": null, "attribute": "capacity", "evidence_reference": "HTML text, text offset 112; context: annual production capacity of 205,000 tonnes of primary aluminium"}]','4b814ef82ba870a0d7786660b0e587eaffa300c6edcab1f299f9e33db1194cda','fixture-pilot-curator','2026-10-13T17:37:40.182659+00:00');
INSERT INTO "evidence_build" VALUES('050de9d997d81225d15a43eb165bd741636d832c5fa0f7dcecf970bb4a7e8b7a','634b38d8-49cf-4188-82bf-bf5c233ba716','a342868ffefabf74e89c2a51ee3c344da564cae8f1344d161d6a9946c0fadff3','industrial-adapters-1.0.0','1.0.0','{"adapter": "pdf-v1", "facility_name": "South Bay Smelter", "country": "AU", "valid_from": "2026-10-10", "valid_to": null, "unit": "t/year", "attribute": "capacity", "prefix": "annual nameplate production capacity of", "suffix": "metric tons", "page": 1}','[{"facility_name": "South Bay Smelter", "country": "AU", "reported_value": "358,000", "unit": "t/year", "valid_from": "2026-10-10", "valid_to": null, "attribute": "capacity", "evidence_reference": "PDF page 1, text offset 133; context: annual nameplate production capacity of 358,000 metric tons"}]','ab347e38a58f08beb7217b62f033c59c1097cf37cf7dba0a7f508f0c004fea66','fixture-pilot-curator','2026-10-13T17:37:40.185502+00:00');
INSERT INTO "evidence_build" VALUES('e707cfcde303beb4146f29a501eaaf9482deb407ff5cb519e0726b2b80bcd01a','83ef134f-280a-4b12-a871-240f9b85a48f','868123cfcafa57f8bb7297c1f6c3bc2845e2321ef523daec273197455f1841d2','industrial-adapters-1.0.0','1.0.0','{"adapter": "csv-v1", "facility_name": null, "country": null, "valid_from": "1970-01-01", "valid_to": null, "unit": "t/year", "attribute": "capacity", "prefix": null, "suffix": null, "page": null}','[{"facility_name": "East Ridge Refinery", "country": "AU", "reported_value": "1.4", "unit": "Mt/year", "valid_from": "2025-01-01", "valid_to": null, "attribute": "capacity", "evidence_reference": "CSV row 2: synthetic test fixture register row East Ridge Refinery"}, {"facility_name": "Ridge Operations", "country": "AU", "reported_value": "9.5", "unit": "Mt/year", "valid_from": "2025-01-01", "valid_to": null, "attribute": "capacity", "evidence_reference": "CSV row 3: synthetic test fixture register row Ridge Operations"}, {"facility_name": "Unknown Lagoon Works", "country": "NZ", "reported_value": "300", "unit": "kt/year", "valid_from": "2025-01-01", "valid_to": null, "attribute": "capacity", "evidence_reference": "CSV row 4: synthetic test fixture register row Unknown Lagoon Works"}]','0206c53cde72c483cbc3adb09c996e97f5d1ce020633eb688abe8f55c2d95583','fixture-pilot-curator','2026-10-13T17:37:40.187334+00:00');
CREATE TABLE facility (
	entity_id VARCHAR NOT NULL, 
	type_code VARCHAR NOT NULL, 
	country_code VARCHAR(2) NOT NULL, 
	region_id VARCHAR, 
	commodity_code VARCHAR NOT NULL, 
	PRIMARY KEY (entity_id), 
	FOREIGN KEY(commodity_code) REFERENCES commodity (code), 
	FOREIGN KEY(country_code) REFERENCES country (code), 
	FOREIGN KEY(entity_id) REFERENCES entities (id), 
	FOREIGN KEY(region_id) REFERENCES region (id), 
	FOREIGN KEY(type_code) REFERENCES facility_type (code)
);
INSERT INTO "facility" VALUES('9fbc621b-31df-5ad7-bd98-91e8864de4cd','smelter','NO',NULL,'aluminium');
INSERT INTO "facility" VALUES('52dcf50b-4407-50b8-9a18-1748413b3f3a','smelter','NO',NULL,'aluminium');
INSERT INTO "facility" VALUES('1af30f84-960f-593d-86e2-2c0193765c6c','smelter','AU',NULL,'aluminium');
INSERT INTO "facility" VALUES('367f7d1a-2e74-5c27-afe0-490d9b5035dd','refinery','AU',NULL,'alumina');
INSERT INTO "facility" VALUES('8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','bauxite_mine','AU',NULL,'bauxite');
CREATE TABLE facility_type (
	code VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (code)
);
INSERT INTO "facility_type" VALUES('smelter','Primary aluminium smelter');
INSERT INTO "facility_type" VALUES('refinery','Alumina refinery');
INSERT INTO "facility_type" VALUES('bauxite_mine','Bauxite mine');
CREATE TABLE market_observations (
	id VARCHAR NOT NULL, 
	instrument VARCHAR NOT NULL, 
	exchange VARCHAR NOT NULL, 
	market VARCHAR NOT NULL, 
	contract_code VARCHAR, 
	prompt_date VARCHAR, 
	commodity VARCHAR NOT NULL, 
	grade VARCHAR, 
	region VARCHAR NOT NULL, 
	price_type VARCHAR NOT NULL, 
	value VARCHAR NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	unit VARCHAR NOT NULL, 
	effective_at VARCHAR NOT NULL, 
	published_at VARCHAR, 
	volume INTEGER, 
	open_interest INTEGER, 
	data_status VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	evidence_reference VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (open_interest IS NULL OR open_interest >= 0), 
	CHECK (volume IS NULL OR volume >= 0), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
);
CREATE TABLE observation_detail (
	observation_id VARCHAR NOT NULL, 
	normalized_value VARCHAR(40), 
	normalized_unit VARCHAR, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	PRIMARY KEY (observation_id), 
	CONSTRAINT ck_detail_unit CHECK (normalized_unit IS NULL OR normalized_unit IN ('t/year','MW','percentage')), 
	CONSTRAINT ck_detail_nonnegative CHECK (normalized_value IS NULL OR normalized_value >= 0), 
	CONSTRAINT ck_detail_interval CHECK (valid_to IS NULL OR valid_to >= valid_from), 
	FOREIGN KEY(observation_id) REFERENCES observations (id)
);
INSERT INTO "observation_detail" VALUES('667a6b09-0f70-4cc8-a939-0842e20cece6','197000','t/year','2024-12-19',NULL);
INSERT INTO "observation_detail" VALUES('f619bb57-428c-4815-b2ee-68522e9caa6e','205000','t/year','2025-06-30',NULL);
INSERT INTO "observation_detail" VALUES('c8cad943-034e-41d9-9ae5-f98d4c90d1aa','358000','t/year','2026-10-10',NULL);
INSERT INTO "observation_detail" VALUES('2376e8c7-fc60-4bd4-99d8-5f040c587622','1400000.0','t/year','2025-01-01',NULL);
INSERT INTO "observation_detail" VALUES('d8800ba9-e1f7-47a1-8a3a-f9aee71ecc02','9500000.0','t/year','2025-01-01',NULL);
INSERT INTO "observation_detail" VALUES('12424ff2-2a05-4326-ae89-2a9baf3ac983',NULL,NULL,'2026-10-10',NULL);
CREATE TABLE "observations" (
	id VARCHAR NOT NULL, 
	entity_id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	attribute VARCHAR NOT NULL, 
	reported_value VARCHAR NOT NULL, 
	reported_unit VARCHAR NOT NULL, 
	normalized_value FLOAT, 
	normalized_unit VARCHAR, 
	valid_from VARCHAR NOT NULL, 
	valid_to VARCHAR, 
	evidence_reference VARCHAR NOT NULL, 
	quality_status VARCHAR NOT NULL, 
	quality_messages JSON NOT NULL, 
	recorded_at VARCHAR NOT NULL, 
	parser_version VARCHAR DEFAULT 'manual-v1' NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_observation_interval CHECK (valid_to IS NULL OR valid_to >= valid_from), 
	CONSTRAINT ck_observation_nonnegative CHECK (normalized_value IS NULL OR normalized_value >= 0), 
	CONSTRAINT ck_observation_dimension CHECK ((attribute='capacity' AND reported_unit IN ('t/year','kt/year','Mt/year')) OR (attribute='power' AND reported_unit='MW') OR (attribute='ownership_percentage' AND reported_unit='percentage') OR (attribute='status' AND reported_unit='status')), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(entity_id) REFERENCES entities (id)
);
INSERT INTO "observations" VALUES('667a6b09-0f70-4cc8-a939-0842e20cece6','9fbc621b-31df-5ad7-bd98-91e8864de4cd','34fb16bf-dc3a-4cae-8a4e-06433fecf541','capacity','197,000','t/year',197000.0,'t/year','2024-12-19',NULL,'HTML text, text offset 112; context: annual production capacity of 197,000 tonnes of primary aluminium','PASS','[]','2026-10-13T17:37:40.180391+00:00','industrial-adapters-1.0.0');
INSERT INTO "observations" VALUES('f619bb57-428c-4815-b2ee-68522e9caa6e','9fbc621b-31df-5ad7-bd98-91e8864de4cd','9436874c-1552-4b8f-951e-a413812e2366','capacity','205,000','t/year',205000.0,'t/year','2025-06-30',NULL,'HTML text, text offset 112; context: annual production capacity of 205,000 tonnes of primary aluminium','PASS','[]','2026-10-13T17:37:40.183401+00:00','industrial-adapters-1.0.0');
INSERT INTO "observations" VALUES('c8cad943-034e-41d9-9ae5-f98d4c90d1aa','1af30f84-960f-593d-86e2-2c0193765c6c','634b38d8-49cf-4188-82bf-bf5c233ba716','capacity','358,000','t/year',358000.0,'t/year','2026-10-10',NULL,'PDF page 1, text offset 133; context: annual nameplate production capacity of 358,000 metric tons','WARN','["Publication date missing"]','2026-10-13T17:37:40.186146+00:00','industrial-adapters-1.0.0');
INSERT INTO "observations" VALUES('2376e8c7-fc60-4bd4-99d8-5f040c587622','367f7d1a-2e74-5c27-afe0-490d9b5035dd','83ef134f-280a-4b12-a871-240f9b85a48f','capacity','1.4','Mt/year',1400000.0,'t/year','2025-01-01',NULL,'CSV row 2: synthetic test fixture register row East Ridge Refinery','PASS','[]','2026-10-13T17:37:40.188002+00:00','industrial-adapters-1.0.0');
INSERT INTO "observations" VALUES('d8800ba9-e1f7-47a1-8a3a-f9aee71ecc02','8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','83ef134f-280a-4b12-a871-240f9b85a48f','capacity','9.5','Mt/year',9500000.0,'t/year','2025-01-01',NULL,'CSV row 3: synthetic test fixture register row Ridge Operations','PASS','[]','2026-10-13T17:37:40.215977+00:00','industrial-adapters-1.0.0');
INSERT INTO "observations" VALUES('12424ff2-2a05-4326-ae89-2a9baf3ac983','9fbc621b-31df-5ad7-bd98-91e8864de4cd','8f4bba96-4edb-4b6c-972a-7f5db7068367','status','operating','status',NULL,NULL,'2026-10-10',NULL,'Fixture operations text: North Fjord Works operating','WARN','["Publication date missing"]','2026-10-13T17:37:40.222505+00:00','manual-v1');
CREATE TABLE paper_accounts (
	id VARCHAR NOT NULL, 
	cash_cents BIGINT NOT NULL, 
	cursor INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (cash_cents >= 0), 
	CHECK (cursor >= 0 AND cursor < 120)
);
INSERT INTO "paper_accounts" VALUES('shared-pilot',10000000,60,0);
CREATE TABLE paper_orders (
	id INTEGER NOT NULL, 
	request_id VARCHAR NOT NULL, 
	instrument VARCHAR NOT NULL, 
	side VARCHAR NOT NULL, 
	order_type VARCHAR NOT NULL, 
	quantity INTEGER NOT NULL, 
	limit_cents INTEGER, 
	fill_cents INTEGER, 
	status VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	filled_at VARCHAR, 
	session_index INTEGER NOT NULL, 
	actor VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (side IN ('buy','sell')), 
	CHECK (status IN ('open','filled','cancelled','expired','settled')), 
	CHECK (quantity > 0), 
	UNIQUE (request_id)
);
CREATE TABLE region (
	id VARCHAR NOT NULL, 
	country_code VARCHAR(2) NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(country_code) REFERENCES country (code), 
	UNIQUE (country_code, name)
);
CREATE TABLE relationships (
	id VARCHAR NOT NULL, 
	company_id VARCHAR NOT NULL, 
	facility_id VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	percentage FLOAT, 
	valid_from VARCHAR NOT NULL, 
	valid_to VARCHAR, 
	document_id VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (role IN ('OWNS','OPERATES')), 
	CHECK (percentage IS NULL OR (percentage >= 0 AND percentage <= 100)), 
	CHECK (valid_to IS NULL OR valid_to >= valid_from), 
	FOREIGN KEY(company_id) REFERENCES entities (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(facility_id) REFERENCES entities (id)
);
INSERT INTO "relationships" VALUES('2e693cb9-ffb0-5f48-8d5f-bc0e92b5cedc','40af3bb6-64f3-532d-a67e-21df04b9cf73','1af30f84-960f-593d-86e2-2c0193765c6c','OWNS',55.0,'2026-10-10',NULL,'634b38d8-49cf-4188-82bf-bf5c233ba716');
INSERT INTO "relationships" VALUES('9090d0d2-dd8b-5060-b255-df20b2c1a065','a96327dc-a6ee-5d81-bb02-d55a816c3fec','1af30f84-960f-593d-86e2-2c0193765c6c','OWNS',22.5,'2026-10-10',NULL,'634b38d8-49cf-4188-82bf-bf5c233ba716');
INSERT INTO "relationships" VALUES('c5b5e5b9-d92a-55da-829d-d990bc829715','0f4617a1-d7e0-5a25-9147-9f00ffbe6b3b','1af30f84-960f-593d-86e2-2c0193765c6c','OWNS',22.5,'2026-10-10',NULL,'634b38d8-49cf-4188-82bf-bf5c233ba716');
INSERT INTO "relationships" VALUES('8b8b76b5-f09a-5807-ac0e-34a090dc6efb','40af3bb6-64f3-532d-a67e-21df04b9cf73','1af30f84-960f-593d-86e2-2c0193765c6c','OPERATES',NULL,'2026-10-10',NULL,'634b38d8-49cf-4188-82bf-bf5c233ba716');
CREATE TABLE retrieval_attempt (
	id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	attempt INTEGER NOT NULL, 
	status VARCHAR NOT NULL, 
	error VARCHAR, 
	http_status INTEGER, 
	recorded_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
);
INSERT INTO "retrieval_attempt" VALUES('5ad50452-721e-4a54-8651-adc8be30b37d','ecc8e14a-e0e0-48c8-a167-c6fe288fa4f6','https://example.org/northern/news/fjord-capacity.html',1,'success',NULL,200,'2026-10-13T17:37:40.152757+00:00');
INSERT INTO "retrieval_attempt" VALUES('e647f263-5330-4494-84d0-9d9a12dae120','4e0ba2ee-d477-428c-854a-9a6387e71275','https://example.org/northern/operations.html',1,'success',NULL,200,'2026-10-13T17:37:40.158199+00:00');
INSERT INTO "retrieval_attempt" VALUES('6d272484-79d7-4315-aa32-6319aa20fedd','c1d2dfef-76d4-46f0-94c4-28f1ea14fb4b','https://example.com/southern/bay-fact-sheet.pdf',1,'success',NULL,200,'2026-10-13T17:37:40.160895+00:00');
INSERT INTO "retrieval_attempt" VALUES('b1997556-6b51-4857-b3b1-e1d00686ee73','3b74d1c6-7f6f-465d-bbb0-a6126d7d154f','https://example.com/southern/register.csv',1,'success',NULL,200,'2026-10-13T17:37:40.163539+00:00');
INSERT INTO "retrieval_attempt" VALUES('ca476023-4d30-4760-a385-9da9e0ce589c','1da9ed97-6d58-4a2a-abeb-912749ff5a35','https://example.org/northern/news/fjord-capacity.html',1,'success',NULL,200,'2026-10-13T17:37:40.165875+00:00');
CREATE TABLE reviews (
	id VARCHAR NOT NULL, 
	raw_name VARCHAR NOT NULL, 
	candidate_ids JSON NOT NULL, 
	status VARCHAR NOT NULL, 
	selected_entity_id VARCHAR, 
	reviewer VARCHAR, 
	reason TEXT, 
	decided_at VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(selected_entity_id) REFERENCES entities (id)
);
INSERT INTO "reviews" VALUES('faccc0aa-c140-425d-bcd0-017012d5c9ae','Ridge Operations','["367f7d1a-2e74-5c27-afe0-490d9b5035dd", "8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4"]','accepted','8dfd5bd5-c155-5144-a6a7-b30cfb5d87f4','local-curator','Register row heading names the bauxite operation of the Ridge pair','2026-10-13T17:37:40.212462+00:00');
INSERT INTO "reviews" VALUES('bf4ca449-62ae-48f9-b72d-1f9a7fa0df71','Unknown Lagoon Works','[]','rejected',NULL,'local-curator','No registered facility matches this fixture name','2026-10-13T17:37:40.219725+00:00');
CREATE TABLE runs (
	id VARCHAR NOT NULL, 
	started_at VARCHAR NOT NULL, 
	pipeline_version VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	manifest JSON NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "runs" VALUES('ecc8e14a-e0e0-48c8-a167-c6fe288fa4f6','2026-10-13T17:37:40.150625+00:00','1.0.0','success','{"source_id": "caab08c6-7026-5cf4-b602-154cc3cdca33", "url": "https://example.org/northern/news/fjord-capacity.html", "adapter": "https-v1", "actor": "fixture-pilot-curator", "document_id": "34fb16bf-dc3a-4cae-8a4e-06433fecf541", "content_hash": "25cfb138a1b164c8ce6e4e0aaaa669d83c2566c11f747592e3b676a062b1ff27", "final_url": "https://example.org/northern/news/fjord-capacity.html", "access_decision_id": "8825ad2e-06e1-4721-934c-a09c5e89c155"}');
INSERT INTO "runs" VALUES('4e0ba2ee-d477-428c-854a-9a6387e71275','2026-10-13T17:37:40.157716+00:00','1.0.0','success','{"source_id": "caab08c6-7026-5cf4-b602-154cc3cdca33", "url": "https://example.org/northern/operations.html", "adapter": "https-v1", "actor": "fixture-pilot-curator", "document_id": "8f4bba96-4edb-4b6c-972a-7f5db7068367", "content_hash": "48badb380aa4ba007433298887f6e956d5dd8b3293922ccaa4ca2fa9dc574165", "final_url": "https://example.org/northern/operations.html", "access_decision_id": "8825ad2e-06e1-4721-934c-a09c5e89c155"}');
INSERT INTO "runs" VALUES('c1d2dfef-76d4-46f0-94c4-28f1ea14fb4b','2026-10-13T17:37:40.160387+00:00','1.0.0','success','{"source_id": "ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8", "url": "https://example.com/southern/bay-fact-sheet.pdf", "adapter": "https-v1", "actor": "fixture-pilot-curator", "document_id": "634b38d8-49cf-4188-82bf-bf5c233ba716", "content_hash": "a342868ffefabf74e89c2a51ee3c344da564cae8f1344d161d6a9946c0fadff3", "final_url": "https://example.com/southern/bay-fact-sheet.pdf", "access_decision_id": "74a6b949-2268-4a7d-a04e-7472d962bca8"}');
INSERT INTO "runs" VALUES('3b74d1c6-7f6f-465d-bbb0-a6126d7d154f','2026-10-13T17:37:40.163111+00:00','1.0.0','success','{"source_id": "ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8", "url": "https://example.com/southern/register.csv", "adapter": "https-v1", "actor": "fixture-pilot-curator", "document_id": "83ef134f-280a-4b12-a871-240f9b85a48f", "content_hash": "868123cfcafa57f8bb7297c1f6c3bc2845e2321ef523daec273197455f1841d2", "final_url": "https://example.com/southern/register.csv", "access_decision_id": "74a6b949-2268-4a7d-a04e-7472d962bca8"}');
INSERT INTO "runs" VALUES('1da9ed97-6d58-4a2a-abeb-912749ff5a35','2026-10-13T17:37:40.165500+00:00','1.0.0','success','{"source_id": "caab08c6-7026-5cf4-b602-154cc3cdca33", "url": "https://example.org/northern/news/fjord-capacity.html", "adapter": "https-v1", "actor": "fixture-pilot-curator", "document_id": "9436874c-1552-4b8f-951e-a413812e2366", "content_hash": "18ae6ed358f32caff1637874b92df569e559c73e15970e538e48ba77ad0c308a", "final_url": "https://example.org/northern/news/fjord-capacity.html", "access_decision_id": "8825ad2e-06e1-4721-934c-a09c5e89c155"}');
INSERT INTO "runs" VALUES('3857ac43-3783-44cf-8df8-1524bd0e0415','2026-10-13T17:37:40.181530+00:00','1.0.0','success','{"adapter": "html-v1", "document_id": "34fb16bf-dc3a-4cae-8a4e-06433fecf541", "build_id": "994dc789e73eaaa8119c1857ca6db1b16ead7d0dddff4661a86ef93686112999", "content_hash": "25cfb138a1b164c8ce6e4e0aaaa669d83c2566c11f747592e3b676a062b1ff27", "parser_version": "industrial-adapters-1.0.0", "output_hash": "f3661084900b89cc75bec6bd0bfe50436e4c4ec1b801024aa43e9ac65bf07ffd"}');
INSERT INTO "runs" VALUES('2e56092a-5c51-4204-a735-f5c78af9ae9d','2026-10-13T17:37:40.183755+00:00','1.0.0','success','{"adapter": "html-v1", "document_id": "9436874c-1552-4b8f-951e-a413812e2366", "build_id": "edb974344f1a272f0b758203a0c63050c5d3275555b4e7c910c9628d9d925ccd", "content_hash": "18ae6ed358f32caff1637874b92df569e559c73e15970e538e48ba77ad0c308a", "parser_version": "industrial-adapters-1.0.0", "output_hash": "4b814ef82ba870a0d7786660b0e587eaffa300c6edcab1f299f9e33db1194cda"}');
INSERT INTO "runs" VALUES('730e9043-80c8-4133-bacc-dba59e38f46c','2026-10-13T17:37:40.186497+00:00','1.0.0','success','{"adapter": "pdf-v1", "document_id": "634b38d8-49cf-4188-82bf-bf5c233ba716", "build_id": "050de9d997d81225d15a43eb165bd741636d832c5fa0f7dcecf970bb4a7e8b7a", "content_hash": "a342868ffefabf74e89c2a51ee3c344da564cae8f1344d161d6a9946c0fadff3", "parser_version": "industrial-adapters-1.0.0", "output_hash": "ab347e38a58f08beb7217b62f033c59c1097cf37cf7dba0a7f508f0c004fea66"}');
INSERT INTO "runs" VALUES('c91e5f3f-d9be-4580-bfa8-6ea4452f9262','2026-10-13T17:37:40.189601+00:00','1.0.0','success','{"adapter": "csv-v1", "document_id": "83ef134f-280a-4b12-a871-240f9b85a48f", "build_id": "e707cfcde303beb4146f29a501eaaf9482deb407ff5cb519e0726b2b80bcd01a", "content_hash": "868123cfcafa57f8bb7297c1f6c3bc2845e2321ef523daec273197455f1841d2", "parser_version": "industrial-adapters-1.0.0", "output_hash": "0206c53cde72c483cbc3adb09c996e97f5d1ce020633eb688abe8f55c2d95583"}');
CREATE TABLE source_access (
	id VARCHAR NOT NULL, 
	source_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	allowed_hosts JSON NOT NULL, 
	basis TEXT NOT NULL, 
	retention TEXT NOT NULL, 
	reviewer VARCHAR NOT NULL, 
	decided_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_source_access_status CHECK (status IN ('permitted','review_required','restricted')), 
	FOREIGN KEY(source_id) REFERENCES sources (id)
);
INSERT INTO "source_access" VALUES('8825ad2e-06e1-4721-934c-a09c5e89c155','caab08c6-7026-5cf4-b602-154cc3cdca33','permitted','["example.org"]','Fixture capture policy for software tests of the pilot pipeline','Fixture only; fictional content','fixture-pilot-curator','2026-10-13T17:37:40.149457+00:00');
INSERT INTO "source_access" VALUES('74a6b949-2268-4a7d-a04e-7472d962bca8','ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8','permitted','["example.com"]','Fixture capture policy for software tests of the pilot pipeline','Fixture only; fictional content','fixture-pilot-curator','2026-10-13T17:37:40.149729+00:00');
CREATE TABLE source_document_relation (
	source_id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	PRIMARY KEY (source_id, document_id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(source_id) REFERENCES sources (id)
);
INSERT INTO "source_document_relation" VALUES('caab08c6-7026-5cf4-b602-154cc3cdca33','34fb16bf-dc3a-4cae-8a4e-06433fecf541');
INSERT INTO "source_document_relation" VALUES('caab08c6-7026-5cf4-b602-154cc3cdca33','8f4bba96-4edb-4b6c-972a-7f5db7068367');
INSERT INTO "source_document_relation" VALUES('ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8','634b38d8-49cf-4188-82bf-bf5c233ba716');
INSERT INTO "source_document_relation" VALUES('ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8','83ef134f-280a-4b12-a871-240f9b85a48f');
INSERT INTO "source_document_relation" VALUES('caab08c6-7026-5cf4-b602-154cc3cdca33','9436874c-1552-4b8f-951e-a413812e2366');
CREATE TABLE source_snapshot (
	content_hash VARCHAR(64) NOT NULL, 
	storage_reference VARCHAR NOT NULL, 
	byte_size INTEGER, 
	PRIMARY KEY (content_hash), 
	CONSTRAINT ck_snapshot_size CHECK (byte_size >= 0)
);
INSERT INTO "source_snapshot" VALUES('25cfb138a1b164c8ce6e4e0aaaa669d83c2566c11f747592e3b676a062b1ff27','25cfb138a1b164c8ce6e4e0aaaa669d83c2566c11f747592e3b676a062b1ff27',279);
INSERT INTO "source_snapshot" VALUES('48badb380aa4ba007433298887f6e956d5dd8b3293922ccaa4ca2fa9dc574165','48badb380aa4ba007433298887f6e956d5dd8b3293922ccaa4ca2fa9dc574165',365);
INSERT INTO "source_snapshot" VALUES('a342868ffefabf74e89c2a51ee3c344da564cae8f1344d161d6a9946c0fadff3','a342868ffefabf74e89c2a51ee3c344da564cae8f1344d161d6a9946c0fadff3',1658);
INSERT INTO "source_snapshot" VALUES('868123cfcafa57f8bb7297c1f6c3bc2845e2321ef523daec273197455f1841d2','868123cfcafa57f8bb7297c1f6c3bc2845e2321ef523daec273197455f1841d2',432);
INSERT INTO "source_snapshot" VALUES('18ae6ed358f32caff1637874b92df569e559c73e15970e538e48ba77ad0c308a','18ae6ed358f32caff1637874b92df569e559c73e15970e538e48ba77ad0c308a',302);
CREATE TABLE sources (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	publisher VARCHAR NOT NULL, 
	source_type VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	access_status VARCHAR NOT NULL, 
	notes TEXT NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "sources" VALUES('caab08c6-7026-5cf4-b602-154cc3cdca33','Example Northern Aluminium public industrial publications','Example Northern Aluminium','company','https://example.org/northern/','permitted','Fictional fixture publisher for software tests. SYNTHETIC TEST FIXTURE - fictional plants and companies, not industrial facts.');
INSERT INTO "sources" VALUES('ef09bbe0-52d1-549d-aa7b-7cb516ba4ac8','Example Southern Smelting public industrial publications','Example Southern Smelting','company','https://example.com/southern/','permitted','Fictional fixture publisher for software tests. SYNTHETIC TEST FIXTURE - fictional plants and companies, not industrial facts.');
CREATE INDEX ix_documents_content_hash ON documents (content_hash);
CREATE INDEX ix_documents_source_id ON documents (source_id);
CREATE INDEX ix_market_observations_effective_at ON market_observations (effective_at);
CREATE INDEX ix_market_observations_instrument ON market_observations (instrument);
CREATE INDEX ix_entity_alias_entity_id ON entity_alias (entity_id);
CREATE INDEX ix_entity_alias_normalized_name ON entity_alias (normalized_name);
CREATE INDEX ix_retrieval_attempt_run_id ON retrieval_attempt (run_id);
CREATE INDEX ix_source_access_source_id ON source_access (source_id);
CREATE INDEX ix_candidate_build_id ON candidate (build_id);
CREATE VIEW facility_alias AS SELECT a.* FROM entity_alias a JOIN entities e ON e.id=a.entity_id WHERE e.kind='facility';
CREATE INDEX ix_observations_entity_id ON observations (entity_id);
CREATE VIEW capacity_observation AS SELECT o.*, d.normalized_value AS exact_value FROM observations o JOIN observation_detail d ON d.observation_id=o.id WHERE o.attribute='capacity';
CREATE VIEW status_observation AS SELECT * FROM observations WHERE attribute='status';
COMMIT;

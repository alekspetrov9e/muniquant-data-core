"""DC1 step B2: generic reads other programs use through the Core API."""

def post(client, path, data):
    response = client.post('/api/' + path, json=data)
    assert response.status_code == 201, response.text
    return response.json()

def test_one_record_by_id(client, example):
    entity, source, document, _ = example
    assert client.get('/api/records/entities/' + entity['id']).json() == entity
    assert client.get('/api/records/documents/' + document['id']).json()['content_hash'] == document['content_hash']
    assert client.get('/api/records/entities/missing').status_code == 404
    assert client.get('/api/records/unknown/' + entity['id']).status_code == 404

def test_equality_filters(client, example):
    entity, source, document, payload = example
    other = post(client, 'documents', {**payload, 'title': 'Other', 'original_url': 'https://example.org/other', 'content': 'Capacity: 5 kt/year'})
    for doc in (document, other):
        post(client, 'observations', {'entity_id': entity['id'], 'document_id': doc['id'], 'reported_value': '400', 'reported_unit': 'kt/year',
                                      'valid_from': '2025-01-01', 'evidence_reference': 'page 1'})
    page = client.get('/api/records/observations', params={'document_id': other['id']}).json()
    assert page['total'] == 1 and [o['document_id'] for o in page['records']] == [other['id']]
    assert client.get('/api/records/documents', params={'version': 1, 'source_id': source['id']}).json()['total'] == 2
    assert {a['action'] for a in client.get('/api/records/audit', params={'action': 'observe'}).json()['records']} == {'observe'}
    # Unknown columns, JSON columns and malformed numbers are refused, never ignored.
    for params in ({'no_such_column': 'x'}, {'aliases': '[]'}, {'version': 'one'}):
        assert client.get('/api/records/documents' if 'version' in params else '/api/records/entities', params=params).status_code == 422

def test_supersessions_are_readable(client, example):
    entity, *_ = example
    survivor = post(client, 'entities', {'name': 'Test Smelter Works', 'country': 'NO', 'facility_type': 'smelter'})
    post(client, 'entities/' + entity['id'] + '/supersession', {'new_entity_id': survivor['id'], 'reason': 'Duplicate identity'})
    page = client.get('/api/records/supersessions').json()
    assert page['total'] == 1 and page['records'][0]['new_entity_id'] == survivor['id']
    assert client.get('/api/records/supersessions/' + entity['id']).json()['new_entity_id'] == survivor['id']

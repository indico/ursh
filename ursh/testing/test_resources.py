import json
from uuid import uuid4

import pytest

from ursh.models import URL, Token


@pytest.fixture
def admin_auth(db):
    return make_auth(db, 'admin', is_admin=True, is_blocked=False)


@pytest.fixture
def non_admin_auth(db):
    return make_auth(db, 'non-admin', is_admin=False, is_blocked=False)


@pytest.fixture
def non_admin_auth_1(db):
    return make_auth(db, 'non-admin-1', is_admin=False, is_blocked=False)


@pytest.fixture
def blocked_auth(db):
    return make_auth(db, 'blocked', is_admin=True, is_blocked=True)


def make_auth(db, name, is_admin=False, is_blocked=False):
    user = create_user(db, name, is_admin, is_blocked)
    return {'Authorization': f'Bearer {user.api_key}'}


def create_user(db, name, is_admin=False, is_blocked=False):
    user = Token()
    user.name = name
    user.is_admin = is_admin
    user.is_blocked = is_blocked
    db.session.add(user)
    db.session.commit()
    return user


# Token tests


@pytest.mark.parametrize("admin,data,expected,status_code", [
    (
        # new token is issued
        True,
        {'name': 'abc', 'is_admin': True, 'callback_url': 'http://cern.ch'},
        {'callback_url': 'http://cern.ch', 'is_admin': True, 'is_blocked': False, 'name': 'abc', 'token_uses': 0},
        201
    ),
    (
        # new token is issued without callback
        True,
        {'name': 'abc', 'is_admin': True},
        {'is_admin': True, 'is_blocked': False, 'name': 'abc', 'token_uses': 0},
        201
    ),
    (
        # name is not mentioned
        True,
        {'is_admin': True, 'callback_url': 'http://cern.ch'},
        {'error': {'args': ['name'], 'code': 'missing-args',
                   'description': 'New tokens need to mention the "name" attribute'}, 'status': 400},
        400
    ),
    (
        # invalid callback URL
        True,
        {'name': 'abc', 'callback_url': 'fake'},
        {'error': {'args': ['callback_url'], 'code': 'validation-error',
                   'messages': {'callback_url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # non-admin attempt
        False,
        {'name': 'abc', 'callback_url': 'http://cern.ch'},
        {'error': {'code': 'insufficient-permissions',
                   'description': 'You are not allowed to make this request'}, 'status': 403},
        403
    )
])
def test_create_token(client, admin_auth, non_admin_auth, admin, data, expected, status_code):
    auth = non_admin_auth
    if admin:
        auth = admin_auth
    response = client.post('/tokens/', data=data, headers=auth)
    parsed_response = json.loads(response.data)

    assert response.status_code == status_code
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status_code == 201:
        token = Token.query.filter_by(name=data['name']).one_or_none()
        assert token is not None
        assert parsed_response.get('api_key') is not None
        assert parsed_response.get('last_access') is not None


def test_create_token_name_exists(client, admin_auth):
    client.post('/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=admin_auth)
    response = client.post('/tokens/', data={'name': 'abc'}, headers=admin_auth)
    expected = {'error': {'args': ['name'], 'code': 'conflict', 'description': 'Token with name exists'}, 'status': 409}

    assert response.status_code == 409
    assert json.loads(response.data) == expected


@pytest.mark.parametrize("admin,url,data,expected,status", [
    (
        # filter based on name
        True,
        '/tokens/',
        {'name': 'abc'},
        [{'callback_url': 'http://cern.ch', 'is_admin': False,
          'is_blocked': False, 'name': 'abc', 'token_uses': 0}],
        200
    ),
    (
        # get all tokens
        True,
        '/tokens/',
        {},
        [{'callback_url': None, 'is_admin': False, 'is_blocked': False, 'name': 'non-admin', 'token_uses': 0},
         {'callback_url': 'http://cern.ch', 'is_admin': False, 'is_blocked': False, 'name': 'abc', 'token_uses': 0},
         {'callback_url': 'http://a.ch', 'is_admin': True, 'is_blocked': True, 'name': 'abcd', 'token_uses': 0},
         {'callback_url': 'http://a.ch', 'is_admin': False, 'is_blocked': True, 'name': 'abcd1', 'token_uses': 0},
         {'callback_url': 'http://b.ch', 'is_admin': False, 'is_blocked': False, 'name': 'abcde', 'token_uses': 0},
         {'callback_url': None, 'is_admin': True, 'is_blocked': False, 'name': 'admin', 'token_uses': 5}],
        200
    ),
    (
        # attempt to get token info by non-admin
        False,
        '/tokens/',
        {},
        {'error': {'code': 'insufficient-permissions',
                   'description': 'You are not allowed to make this request'}, 'status': 403},
        403
    ),
    (
        # attempt to get specific token info with invalid UUID
        True,
        '/tokens/abc',
        {},
        {'error': {'args': ['api_key'], 'code': 'not-found', 'description': 'API key does not exist'},
         'status': 404},
        404
    ),
    (
        # access specific token from non-admin
        False,
        '/tokens/abc',
        {},
        {'error': {'code': 'insufficient-permissions',
                   'description': 'You are not allowed to make this request'}, 'status': 403},
        403
    ),
    (
        # filter based on other parameters
        True,
        '/tokens/',
        {'callback_url': 'http://a.ch', 'is_admin': False},
        [{'callback_url': 'http://a.ch', 'is_admin': False, 'is_blocked': True, 'name': 'abcd1', 'token_uses': 0}],
        200
    )
])
def test_get_tokens(client, admin_auth, non_admin_auth, admin, url, data, expected, status):
    auth = non_admin_auth
    if admin:
        auth = admin_auth
    client.post('/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=auth)
    client.post('/tokens/', data={'name': 'abcd', 'callback_url': 'http://a.ch',
                                  'is_admin': True, 'is_blocked': True}, headers=auth)
    client.post('/tokens/', data={'name': 'abcd1', 'callback_url': 'http://a.ch',
                                  'is_admin': False, 'is_blocked': True}, headers=auth)
    client.post('/tokens/', data={'name': 'abcde', 'callback_url': 'http://b.ch'}, headers=auth)
    response = client.get(url, query_string=data, headers=auth)
    parsed_response = json.loads(response.data)

    assert response.status_code == status
    if type(expected) == list:
        parsed_response = sorted(parsed_response, key=lambda k: k['name'])
        expected = sorted(expected, key=lambda k: k['name'])
        for expected_token, returned_token in zip(expected, parsed_response):
            for key, value in expected_token.items():
                assert value == returned_token[key]
            if status == 200:
                assert returned_token.get('api_key') is not None
                assert returned_token.get('last_access') is not None
    else:
        for key, value in expected.items():
            assert value == parsed_response[key]
        if status == 200:
            assert parsed_response.get('api_key') is not None
            assert parsed_response.get('last_access') is not None


@pytest.mark.parametrize("admin,name,data,expected,status", [
    (
        # everything goes right
        True,
        'abc',
        {'callback_url': 'http://www.google.com', 'is_admin': True, 'is_blocked': True},
        {'callback_url': 'http://www.google.com', 'is_admin': True, 'is_blocked': True, 'name': 'abc', 'token_uses': 0},
        200
    ),
    (
        # try to change the name
        True,
        'abc',
        {'name': 'xyz', 'callback_url': 'http://www.google.com', 'is_admin': True, 'is_blocked': True},
        {'callback_url': 'http://www.google.com', 'is_admin': True, 'is_blocked': True,
         'name': 'abc', 'token_uses': 0},
        200
    ),
    (
        # invalid name
        True,
        'abcdef',
        {'callback_url': 'http://www.google.com', 'is_admin': True, 'is_blocked': True},
        {'error': {'args': ['api_key'], 'code': 'not-found', 'description': 'API key does not exist'},
         'status': 404},
        404
    ),
    (
        # non-existent api key
        True,
        str(uuid4()),
        {'callback_url': 'http://www.google.com', 'is_admin': True, 'is_blocked': True},
        {'error': {'args': ['api_key'], 'code': 'not-found', 'description': 'API key does not exist'}, 'status': 404},
        404
    ),
    (
        # non-admin access attempt
        False,
        'abc',
        {'callback_url': 'http://www.google.com', 'is_admin': True, 'is_blocked': True},
        {'error': {'code': 'insufficient-permissions',
                   'description': 'You are not allowed to make this request'}, 'status': 403},
        403
    )
])
def test_token_patch(client, admin_auth, non_admin_auth, admin, name, data, expected, status):
    auth = non_admin_auth
    if admin:
        auth = admin_auth
    client.post('/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=auth)
    client.post('/tokens/', data={'name': 'abcd', 'callback_url': 'http://a.ch',
                                  'is_admin': True, 'is_blocked': True}, headers=auth)
    client.post('/tokens/', data={'name': 'abcd1', 'callback_url': 'http://a.ch',
                                  'is_admin': False, 'is_blocked': True}, headers=auth)
    client.post('/tokens/', data={'name': 'abcde', 'callback_url': 'http://b.ch'}, headers=auth)
    token = Token.query.filter_by(name=name).one_or_none()
    uuid = token.api_key if token else name  # assume we want to use the name as an API key if it is not present
    response = client.patch(f'/tokens/{uuid}', query_string=data, headers=auth)
    parsed_response = json.loads(response.data)
    assert response.status_code == status
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status == 200:
        token = Token.query.filter_by(name=name).one_or_none()
        assert token is not None
        assert parsed_response.get('api_key') is not None
        assert parsed_response.get('last_access') is not None
        assert token.callback_url == data.get('callback_url')
        assert token.is_admin == data.get('is_admin')
        assert token.is_blocked == data.get('is_blocked')


@pytest.mark.parametrize("admin,expected,status", [
    (True, '', 204),
    (False, {"error": {"code": "insufficient-permissions",
                       "description": "You are not allowed to make this request"}, "status": 403}, 403)
])
def test_token_delete(client, admin_auth, non_admin_auth, admin, expected, status):
    auth = non_admin_auth
    if admin:
        auth = admin_auth
    client.post('/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=admin_auth)
    api_key = Token.query.filter_by(name='abc').one_or_none().api_key
    response = client.delete(f'/tokens/{api_key}', headers=auth)

    assert response.status_code == status
    if status == 204:
        assert response.data == b''
    else:
        assert json.loads(response.data) == expected


@pytest.mark.parametrize("method,url,data", [
    ('post', '/tokens/', {'name': 'abc', 'callback_url': 'http://cern.ch'}),
    ('get', '/tokens/', {}),
    ('patch', '/tokens/abc', {}),
    ('delete', '/tokens/abc', {}),
    ('post', '/urls/', {'url': 'abc'}),
    ('get', '/urls/', {}),
    ('patch', '/urls/abc', {}),
    ('delete', '/urls/abc', {}),
    ('put', '/urls/abc', {})
])
@pytest.mark.parametrize("blocked", [True, False])
def test_blocked_or_unauthorized(client, blocked_auth, method, url, data, blocked):
    headers = None
    if blocked:
        headers = blocked_auth
    method = getattr(client, method)
    response = method(url, query_string=data, headers=headers)
    expected = {'error': {'code': 'invalid-token',
                          'description': 'The token you have entered is invalid'},
                'status': 401}

    assert response.status_code == 401
    assert json.loads(response.data) == expected


# URL Tests


@pytest.mark.parametrize("data,expected,status", [
    (
        # everything works right, a new url is created
        {'url': 'http://cern.ch'},
        {'metadata': '{}', 'url': 'http://cern.ch'},
        201
    ),
    (
        # everything works right, a new url is created with metadata
        {'url': 'http://cern.ch', 'metadata.author': 'me', 'metadata.a': False},
        {'metadata': '{"author": "me", "a": "False"}', 'url': 'http://cern.ch'},
        201
    ),
    (
        # invalid url
        {'url': 'fake'},
        {'error': {'args': ['url'], 'code': 'validation-error',
                   'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # empty url
        {'url': ''},
        {'error': {'args': ['url'], 'code': 'validation-error',
                   'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # allow_reuse=true
        {'url': 'http://existing.com', 'allow_reuse': True},
        {'metadata': '{}', 'url': 'http://existing.com'},
        400
    )
])
def test_create_url(app, client, non_admin_auth, data, expected, status):
    existing_shortcut = ''
    if data.get('allow_reuse'):
        existing = client.post('/urls/', query_string={'url': 'http://existing.com'}, headers=non_admin_auth)
        existing = json.loads(existing.data)
        existing_shortcut = existing.get('shortcut')
        assert existing_shortcut is not None
    response = client.post('/urls/', query_string=data, headers=non_admin_auth)
    parsed_response = json.loads(response.data)
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status == 201:
        if data.get('allow_reuse'):
            assert data.get('shortcut') == existing_shortcut
        assert parsed_response.get('shortcut') is not None
        assert parsed_response.get('token') is not None
        url = URL.query.filter_by(shortcut=parsed_response['shortcut']).one_or_none()
        assert url is not None
        assert url.url == data['url']
        assert len(url.shortcut) == app.config.get('URL_LENGTH')
        assert response.status_code == status


@pytest.mark.parametrize("name,data,expected,status", [
    (
        # everything goes right
        "my-short-url",
        {'url': 'http://google.com', 'metadata.author': 'me'},
        {'metadata': '{"author": "me"}', 'shortcut': 'my-short-url', 'url': 'http://google.com'},
        201
    ),
    (
        # pre-existing url
        "i-exist",
        {'url': 'http://google.com', 'metadata.author': 'me'},
        {'error': {'args': ['shortcut'], 'code': 'conflict', 'description': 'Shortcut already exists'}, 'status': 409},
        409
    ),
    (
        # allow_reuse = true
        "i-exist",
        {'url': 'http://cern.ch', 'metadata.author': 'me', 'allow_reuse': True},
        {'metadata': '{}', 'shortcut': 'i-exist', 'url': 'http://example.com'},
        201
    ),
    (
        # invalid url
        "my-short-url",
        {'url': 'google.com', 'metadata.author': 'me'},
        {'error': {'args': ['url'], 'code': 'validation-error',
                   'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # empty url
        "my-short-url",
        {'url': '', 'metadata.author': 'me'},
        {'error': {'args': ['url'], 'code': 'validation-error',
                   'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # url with invalid characters
        "my-short-url*",
        {'url': 'https://google.com', 'metadata.author': 'me'},
        {'error': {'args': ['shortcut'], 'code': 'validation-error',
                   'messages': {'shortcut': ['Invalid value.']}}, 'status': 400},
        400
    ),
    (
        # url with slash
        "my-short-url/i-look-suspicious*",
        {'url': 'https://google.com', 'metadata.author': 'me'},
        {},
        404
    ),
    (
        # blacklisted URL
        "tokens",
        {'url': '', 'metadata.author': 'me'},
        {'error': {'args': ['shortcut', 'url'], 'code': 'validation-error',
                   'messages': {'shortcut': ['Invalid value.'], 'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
])
def test_put_url(client, non_admin_auth, name, data, expected, status):
    client.put('/urls/i-exist', query_string={'url': 'http://example.com'}, headers=non_admin_auth)
    response = client.put(f'/urls/{name}', query_string=data, headers=non_admin_auth)
    assert response.status_code == status
    if status == 404:
        return
    parsed_response = json.loads(response.data)
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status == 200:
        assert parsed_response.get('shortcut') is not None
        assert parsed_response.get('token') is not None
        url = URL.query.filter_by(shortcut=name)
        assert url is not None


@pytest.mark.parametrize("shortcut,data,expected,status", [
    (
        # everything goes right
        "abc",
        {'metadata.author': 'me', 'url': 'http://example.com'},
        {'metadata': '{"author": "me"}', 'shortcut': 'abc', 'url': 'http://example.com'},
        200
    ),
    (
        # nonexistent shortcut
        "nonexistent",
        {'metadata.author': 'me', 'url': 'http://example.com'},
        {'error': {'args': ['shortcut'], 'code': 'not-found', 'description': 'Shortcut does not exist'}, 'status': 404},
        404
    ),
    (
        # invalid url
        "abc",
        {'metadata.author': 'me', 'url': 'example.com'},
        {'error': {'args': ['url'], 'code': 'validation-error',
                   'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # empty url
        "abc",
        {'metadata.author': 'me', 'url': ''},
        {'error': {'args': ['url'], 'code': 'validation-error',
                   'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
])
def test_patch_url(client, non_admin_auth, non_admin_auth_1, shortcut, data, expected, status):
    client.put('/urls/abc', query_string={'url': 'http://example.com'}, headers=non_admin_auth)
    client.put('/urls/def', query_string={'url': 'http://example.com'}, headers=non_admin_auth)
    response = client.patch(f'/urls/{shortcut}', query_string=data, headers=non_admin_auth)
    parsed_response = json.loads(response.data)
    assert response.status_code == status
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status == 200:
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        assert url is not None
        assert parsed_response.get('shortcut') is not None
        assert parsed_response.get('token') is not None
        assert url.url == data.get('url')
        assert url.token.api_key == parsed_response.get('token')


@pytest.mark.parametrize("shortcut,expected,status", [
    (
        # everything goes right
        "abc",
        {},
        204
    ),
    (
        # invalid shortcut
        "abcd",
        {'error': {'args': ['shortcut'], 'code': 'not-found', 'description': 'Shortcut does not exist'}, 'status': 404},
        404
    ),
])
def test_delete_url(client, non_admin_auth, shortcut, expected, status):
    client.put('/urls/abc', query_string={'url': 'http://example.com'}, headers=non_admin_auth)
    client.put('/urls/def', query_string={'url': 'http://example.com'}, headers=non_admin_auth)
    response = client.delete(f'/urls/{shortcut}', headers=non_admin_auth)
    assert response.status_code == status
    if status == 204:
        url = URL.query.filter_by(shortcut='abc').one_or_none()
        assert url is None
        assert response.data == b''
    else:
        parsed_response = json.loads(response.data)
        for key, value in expected.items():
            assert value == parsed_response[key]


@pytest.mark.parametrize("url,data,expected,status", [
    (
        # everything goes right
        '/urls/',
        {},
        [{'metadata': '{"author": "me"}', 'shortcut': 'abc', 'url': 'http://example.com'},
         {'metadata': '{"a": "b", "owner": "all"}', 'shortcut': 'def', 'url': 'http://example.com'},
         {'metadata': '{"author": "me"}', 'shortcut': 'ghi', 'url': 'http://cern.ch'}],
        200
    ),
    (
        # everything goes right, asking for specific shortcut
        '/urls/abc',
        {},
        {'metadata': '{"author": "me"}', 'shortcut': 'abc', 'url': 'http://example.com'},
        200
    ),
    (
        # filter based on url
        '/urls/',
        {'url': 'http://example.com'},
        [{'metadata': '{"author": "me"}', 'shortcut': 'abc', 'url': 'http://example.com'},
         {'metadata': '{"a": "b", "owner": "all"}', 'shortcut': 'def', 'url': 'http://example.com'}],
        200
    ),
    (
        # filter based on metadata fields
        '/urls/',
        {'metadata.author': 'me'},
        [{'metadata': '{"author": "me"}', 'shortcut': 'abc', 'url': 'http://example.com'},
         {'metadata': '{"author": "me"}', 'shortcut': 'ghi', 'url': 'http://cern.ch'}],
        200
    ),
    (
        # filter based on both url and metadata fields
        '/urls/',
        {'url': 'http://example.com', 'metadata.author': 'me'},
        [{'metadata': '{"author": "me"}', 'shortcut': 'abc', 'url': 'http://example.com'}],
        200
    ),
    (
        # invalid shortcut
        '/urls/xyz',
        {},
        {'error': {'args': ['shortcut'], 'code': 'not-found', 'description': 'Shortcut does not exist'}, 'status': 404},
        404
    )
])
def test_get_url(client, non_admin_auth, url, data, expected, status):
    client.put('/urls/abc', query_string={'url': 'http://example.com', 'metadata.author': 'me'}, headers=non_admin_auth)
    client.put('/urls/def', query_string={'url': 'http://example.com', 'metadata.owner': 'all', 'metadata.a': 'b'},
               headers=non_admin_auth)
    client.put('/urls/ghi', query_string={'url': 'http://cern.ch', 'metadata.author': 'me'}, headers=non_admin_auth)
    response = client.get(url, query_string=data, headers=non_admin_auth)
    parsed_response = json.loads(response.data)

    assert response.status_code == status
    if type(expected) == list:
        parsed_response = sorted(parsed_response, key=lambda k: k['shortcut'])
        expected = sorted(expected, key=lambda k: k['shortcut'])
        for expected_token, returned_token in zip(expected, parsed_response):
            for key, value in expected_token.items():
                assert value == returned_token[key]
            if status == 200:
                assert returned_token.get('token') is not None
                assert returned_token.get('url') is not None
    else:
        for key, value in expected.items():
            assert value == parsed_response[key]
        if status == 200:
            assert parsed_response.get('token') is not None
            assert parsed_response.get('url') is not None


def test_get_admin_all(client, admin_auth, non_admin_auth, non_admin_auth_1):
    client.put('/urls/abc', query_string={'url': 'http://example.com', 'metadata.author': 'me'}, headers=non_admin_auth)
    client.put('/urls/def', query_string={'url': 'http://example.com', 'metadata.owner': 'all', 'metadata.a': 'b'},
               headers=non_admin_auth_1)
    client.put('/urls/ghi', query_string={'url': 'http://cern.ch', 'metadata.author': 'me'}, headers=admin_auth)
    response = client.get('/urls/', query_string={'all': True}, headers=admin_auth)
    parsed_response = json.loads(response.data)
    expected = [{'metadata': '{"author": "me"}', 'shortcut': 'abc', 'url': 'http://example.com'},
                {'metadata': '{"a": "b", "owner": "all"}', 'shortcut': 'def', 'url': 'http://example.com'},
                {'metadata': '{"author": "me"}', 'shortcut': 'ghi', 'url': 'http://cern.ch'}]
    assert response.status_code == 200
    parsed_response = sorted(parsed_response, key=lambda k: k['url'])
    expected = sorted(expected, key=lambda k: k['url'])
    for expected_token, returned_token in zip(expected, parsed_response):
        for key, value in expected_token.items():
            assert value == returned_token[key]
        assert returned_token.get('token') is not None
        assert returned_token.get('url') is not None


@pytest.mark.parametrize("method", ['patch', 'delete'])
def test_other_user(client, non_admin_auth, non_admin_auth_1, method):
    client.put('/urls/abc', query_string={'url': 'http://example.com', 'metadata.author': 'me'}, headers=non_admin_auth)
    method = getattr(client, method)
    response = method('/urls/abc', query_string={}, headers=non_admin_auth_1)
    expected = {'error': {'code': 'insufficient-permissions',
                          'description': 'You are not allowed to make this request'},
                'status': 403}
    assert response.status_code == 403
    assert json.loads(response.data) == expected

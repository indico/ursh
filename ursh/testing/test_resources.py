import posixpath
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from ursh.models import URL, Token


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
        {'error': {'code': 'validation-error', 'messages': {'callback_url': ['Not a valid URL.']}}, 'status': 400},
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
def test_create_token(db, client, admin, data, expected, status_code):
    if admin:
        auth = make_auth(db, 'admin', is_admin=True, is_blocked=False)
    else:
        auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)
    response = client.post('/api/tokens/', data=data, headers=auth)
    parsed_response = response.get_json()

    assert response.status_code == status_code
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status_code == 201:
        token = Token.query.filter_by(name=data['name']).one_or_none()
        assert token is not None
        assert parsed_response.get('api_key') is not None
        assert parsed_response.get('last_access') is not None


def test_create_token_name_exists(db, client):
    auth = make_auth(db, 'admin', is_admin=True, is_blocked=False)
    client.post('/api/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=auth)
    response = client.post('/api/tokens/', data={'name': 'abc'}, headers=auth)
    expected = {'error': {'args': ['name'], 'code': 'conflict', 'description': 'Token with name exists'}, 'status': 409}

    assert response.status_code == 409
    assert response.get_json() == expected


@pytest.mark.parametrize("admin,url,data,expected,status", [
    (
        # filter based on name
        True,
        '/api/tokens/',
        {'name': 'abc'},
        [{'callback_url': 'http://cern.ch', 'is_admin': False,
          'is_blocked': False, 'name': 'abc', 'token_uses': 0}],
        200
    ),
    (
        # get all tokens
        True,
        '/api/tokens/',
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
        '/api/tokens/',
        {},
        {'error': {'code': 'insufficient-permissions',
                   'description': 'You are not allowed to make this request'}, 'status': 403},
        403
    ),
    (
        # attempt to get specific token info with invalid UUID
        True,
        '/api/tokens/abc',
        {},
        {'error': {'args': ['api_key'], 'code': 'not-found', 'description': 'API key does not exist'},
         'status': 404},
        404
    ),
    (
        # access specific token from non-admin
        False,
        '/api/tokens/abc',
        {},
        {'error': {'code': 'insufficient-permissions',
                   'description': 'You are not allowed to make this request'}, 'status': 403},
        403
    ),
    (
        # filter based on other parameters
        True,
        '/api/tokens/',
        {'callback_url': 'http://a.ch', 'is_admin': False},
        [{'callback_url': 'http://a.ch', 'is_admin': False, 'is_blocked': True, 'name': 'abcd1', 'token_uses': 0}],
        200
    )
])
def test_get_tokens(db, client, admin, url, data, expected, status):
    if admin:
        auth = make_auth(db, 'admin', is_admin=True, is_blocked=False)
    else:
        auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)

    client.post('/api/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=auth)
    client.post('/api/tokens/', data={'name': 'abcd', 'callback_url': 'http://a.ch',
                                      'is_admin': True, 'is_blocked': True}, headers=auth)
    client.post('/api/tokens/', data={'name': 'abcd1', 'callback_url': 'http://a.ch',
                                      'is_admin': False, 'is_blocked': True}, headers=auth)
    client.post('/api/tokens/', data={'name': 'abcde', 'callback_url': 'http://b.ch'}, headers=auth)
    response = client.get(url, query_string=data, headers=auth)
    parsed_response = response.get_json()

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
def test_token_patch(db, client, admin, name, data, expected, status):
    if admin:
        auth = make_auth(db, 'admin', is_admin=True, is_blocked=False)
    else:
        auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)

    client.post('/api/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=auth)
    client.post('/api/tokens/', data={'name': 'abcd', 'callback_url': 'http://a.ch',
                                      'is_admin': True, 'is_blocked': True}, headers=auth)
    client.post('/api/tokens/', data={'name': 'abcd1', 'callback_url': 'http://a.ch',
                                      'is_admin': False, 'is_blocked': True}, headers=auth)
    client.post('/api/tokens/', data={'name': 'abcde', 'callback_url': 'http://b.ch'}, headers=auth)
    token = Token.query.filter_by(name=name).one_or_none()
    uuid = token.api_key if token else name  # assume we want to use the name as an API key if it is not present
    response = client.patch(f'/api/tokens/{uuid}', query_string=data, headers=auth)
    parsed_response = response.get_json()

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
def test_token_delete(db, client, admin, expected, status):
    if admin:
        auth = make_auth(db, 'admin', is_admin=True, is_blocked=False)
    else:
        auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)
    admin_auth = make_auth(db, 'admin_', is_admin=True, is_blocked=False)

    client.post('/api/tokens/', data={'name': 'abc', 'callback_url': 'http://cern.ch'}, headers=admin_auth)
    api_key = Token.query.filter_by(name='abc').one_or_none().api_key
    response = client.delete(f'/api/tokens/{api_key}', headers=auth)

    assert response.status_code == status
    if status == 204:
        assert response.data == b''
    else:
        assert response.get_json() == expected


@pytest.mark.parametrize("method,url,data", [
    ('post', '/api/tokens/', {'name': 'abc', 'callback_url': 'http://cern.ch'}),
    ('get', '/api/tokens/', {}),
    ('patch', '/api/tokens/abc', {}),
    ('delete', '/api/tokens/abc', {}),
    ('post', '/api/urls/', {'url': 'abc'}),
    ('get', '/api/urls/', {}),
    ('patch', '/api/urls/abc', {}),
    ('delete', '/api/urls/abc', {}),
    ('put', '/api/urls/abc', {})
])
@pytest.mark.parametrize("blocked", [True, False])
def test_blocked_or_unauthorized(db, client, method, url, data, blocked):
    headers = make_auth(db, 'blocked', is_admin=True, is_blocked=True) if blocked else None

    method = getattr(client, method)
    response = method(url, query_string=data, headers=headers)
    expected = {'error': {'code': 'invalid-token',
                          'description': 'The token you have entered is invalid'},
                'status': 401}

    assert response.status_code == 401
    assert response.get_json() == expected


# URL Tests

@pytest.mark.parametrize("data,expected,status", [
    (
        # everything works right, a new url is created
        {'url': 'http://cern.ch'},
        {'meta': {}, 'url': 'http://cern.ch'},
        201
    ),
    (
        # everything works right, a new url is created with metadata
        {'url': 'http://cern.ch', 'meta.author': 'me', 'meta.a': False},
        {'meta': {"author": "me", "a": "False"}, 'url': 'http://cern.ch'},
        201
    ),
    (
        # invalid url
        {'url': 'fake'},
        {'error': {'code': 'validation-error', 'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # empty url
        {'url': ''},
        {'error': {'code': 'validation-error', 'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # allow_reuse=true
        {'url': 'http://existing.com', 'allow_reuse': True},
        {'meta': {}, 'url': 'http://existing.com'},
        400
    )
])
def test_create_url(db, app, client, data, expected, status):
    auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)

    existing_shortcut = ''
    if data.get('allow_reuse'):
        existing = client.post('/api/urls/', query_string={'url': 'http://existing.com'}, headers=auth)
        existing = existing.get_json()
        existing_short_url = existing.get('short_url')
        assert existing_short_url is not None
    response = client.post('/api/urls/', query_string=data, headers=auth)
    parsed_response = response.get_json()

    for key, value in expected.items():
        assert value == parsed_response[key]
    if status == 201:
        if data.get('allow_reuse'):
            assert data.get('shortcut') == existing_shortcut
        assert parsed_response.get('short_url') is not None
        assert parsed_response.get('owner') is not None
        shortcut = urlparse(parsed_response['short_url']).path.lstrip('/')
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        assert url is not None
        assert url.url == data['url']
        assert len(url.shortcut) == app.config.get('URL_LENGTH')
        assert response.status_code == status


@pytest.mark.parametrize("name,data,expected,status", [
    (
        # everything goes right
        "my-short-url",
        {'url': 'http://google.com', 'meta.author': 'me'},
        {'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'my-short-url'),
         'url': 'http://google.com'},
        201
    ),
    (
        # invalid url
        "my-short-url",
        {'url': 'google.com', 'meta.author': 'me'},
        {'error': {'code': 'validation-error', 'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # empty url
        "my-short-url",
        {'url': '', 'meta.author': 'me'},
        {'error': {'code': 'validation-error', 'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # url with invalid characters
        "my-short-url*",
        {'url': 'https://google.com', 'meta.author': 'me'},
        {'error': {'code': 'validation-error', 'messages': {'shortcut': ['Invalid value.']}}, 'status': 400},
        400
    ),
    (
        # url with slash
        "my-short-url/i-look-suspicious",
        {'url': 'https://google.com', 'meta.author': 'me'},
        {},
        404
    ),
    (
        # blacklisted URL
        "api",
        {'url': '', 'meta.author': 'me'},
        {'error': {'code': 'validation-error',
                   'messages': {'shortcut': ['Invalid value.'], 'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
])
def test_put_url(db, client, name, data, expected, status):
    auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)

    client.put('/api/urls/i-exist', query_string={'url': 'http://example.com'}, headers=auth)
    response = client.put(f'/api/urls/{name}', query_string=data, headers=auth)
    parsed_response = response.get_json()

    assert response.status_code == status
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status == 200:
        assert parsed_response.get('short_url') is not None
        assert parsed_response.get('owner') is not None
        url = URL.query.filter_by(shortcut=name)
        assert url is not None


@pytest.mark.parametrize("shortcut,data,expected,status", [
    (
        # everything goes right
        "abc",
        {'meta.author': 'me', 'url': 'http://example.com'},
        {'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'abc'),
         'url': 'http://example.com'},
        200
    ),
    (
        # nonexistent shortcut
        "nonexistent",
        {'meta.author': 'me', 'url': 'http://example.com'},
        {'error': {'args': ['shortcut'], 'code': 'not-found', 'description': 'Shortcut does not exist'}, 'status': 404},
        404
    ),
    (
        # invalid url
        "abc",
        {'meta.author': 'me', 'url': 'example.com'},
        {'error': {'code': 'validation-error', 'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
    (
        # empty url
        "abc",
        {'meta.author': 'me', 'url': ''},
        {'error': {'code': 'validation-error', 'messages': {'url': ['Not a valid URL.']}}, 'status': 400},
        400
    ),
])
def test_patch_url(db, client, shortcut, data, expected, status):
    auth1 = make_auth(db, 'non-admin-1', is_admin=False, is_blocked=False)
    auth2 = make_auth(db, 'non-admin-2', is_admin=False, is_blocked=False)

    client.put('/api/urls/abc', query_string={'url': 'http://example.com'}, headers=auth1)
    client.put('/api/urls/def', query_string={'url': 'http://example.com'}, headers=auth2)
    response = client.patch(f'/api/urls/{shortcut}', query_string=data, headers=auth1)
    parsed_response = response.get_json()

    assert response.status_code == status
    for key, value in expected.items():
        assert value == parsed_response[key]
    if status == 200:
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        assert url is not None
        assert parsed_response.get('short_url') is not None
        assert parsed_response.get('owner') is not None
        assert url.url == data.get('url')
        assert url.token.name == parsed_response.get('owner')


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
def test_delete_url(db, client, shortcut, expected, status):
    auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)

    client.put('/api/urls/abc', query_string={'url': 'http://example.com'}, headers=auth)
    client.put('/api/urls/def', query_string={'url': 'http://example.com'}, headers=auth)
    response = client.delete(f'/api/urls/{shortcut}', headers=auth)

    assert response.status_code == status
    if status == 204:
        url = URL.query.filter_by(shortcut='abc').one_or_none()
        assert url is None
        assert response.data == b''
    else:
        parsed_response = response.get_json()
        for key, value in expected.items():
            assert value == parsed_response[key]


@pytest.mark.parametrize("url,data,expected,status", [
    (
        # everything goes right
        '/api/urls/',
        {},
        [{'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'abc'),
          'url': 'http://example.com'},
         {'meta': {"a": "b", "owner": "all"}, 'short_url': posixpath.join('http://localhost:5000/', 'def'),
          'url': 'http://example.com'},
         {'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'ghi'),
          'url': 'http://cern.ch'}],
        200
    ),
    (
        # everything goes right, asking for specific shortcut
        '/api/urls/abc',
        {},
        {'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'abc'),
         'url': 'http://example.com'},
        200
    ),
    (
        # filter based on url
        '/api/urls/',
        {'url': 'http://example.com'},
        [{'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'abc'),
          'url': 'http://example.com'},
         {'meta': {"a": "b", "owner": "all"}, 'short_url': posixpath.join('http://localhost:5000/', 'def'),
          'url': 'http://example.com'}],
        200
    ),
    (
        # filter based on metadata fields
        '/api/urls/',
        {'meta.author': 'me'},
        [{'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'abc'),
          'url': 'http://example.com'},
         {'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'ghi'),
          'url': 'http://cern.ch'}],
        200
    ),
    (
        # filter based on both url and metadata fields
        '/api/urls/',
        {'url': 'http://example.com', 'meta.author': 'me'},
        [{'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'abc'),
          'url': 'http://example.com'}],
        200
    ),
    (
        # invalid shortcut
        '/api/urls/xyz',
        {},
        {'error': {'args': ['shortcut'], 'code': 'not-found', 'description': 'Shortcut does not exist'}, 'status': 404},
        404
    )
])
def test_get_url(db, client, url, data, expected, status):
    auth = make_auth(db, 'non-admin', is_admin=False, is_blocked=False)

    client.put('/api/urls/abc', query_string={'url': 'http://example.com', 'meta.author': 'me'}, headers=auth)
    client.put('/api/urls/def', query_string={'url': 'http://example.com', 'meta.owner': 'all', 'meta.a': 'b'},
               headers=auth)
    client.put('/api/urls/ghi', query_string={'url': 'http://cern.ch', 'meta.author': 'me'}, headers=auth)
    response = client.get(url, query_string=data, headers=auth)
    parsed_response = response.get_json()

    assert response.status_code == status
    if type(expected) == list:
        parsed_response = sorted(parsed_response, key=lambda k: k['short_url'])
        expected = sorted(expected, key=lambda k: k['short_url'])
        for expected_token, returned_token in zip(expected, parsed_response):
            for key, value in expected_token.items():
                assert value == returned_token[key]
            if status == 200:
                assert returned_token.get('owner') is not None
                assert returned_token.get('url') is not None
    else:
        for key, value in expected.items():
            assert value == parsed_response[key]
        if status == 200:
            assert parsed_response.get('owner') is not None
            assert parsed_response.get('url') is not None


def test_get_admin_all(db, client):
    admin_auth = make_auth(db, 'admin', is_admin=True, is_blocked=False)
    non_admin_auth1 = make_auth(db, 'non-admin-1', is_admin=False, is_blocked=False)
    non_admin_auth2 = make_auth(db, 'non-admin-2', is_admin=False, is_blocked=False)

    client.put('/api/urls/abc', query_string={'url': 'http://example.com', 'meta.author': 'me'},
               headers=non_admin_auth1)
    client.put('/api/urls/def', query_string={'url': 'http://example.com', 'meta.owner': 'all', 'meta.a': 'b'},
               headers=non_admin_auth2)
    client.put('/api/urls/ghi', query_string={'url': 'http://cern.ch', 'meta.author': 'me'}, headers=admin_auth)
    response = client.get('/api/urls/', query_string={'all': True}, headers=admin_auth)
    parsed_response = response.get_json()
    expected = [{'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'abc'),
                 'url': 'http://example.com'},
                {'meta': {"a": "b", "owner": "all"}, 'short_url': posixpath.join('http://localhost:5000/', 'def'),
                 'url': 'http://example.com'},
                {'meta': {"author": "me"}, 'short_url': posixpath.join('http://localhost:5000/', 'ghi'),
                 'url': 'http://cern.ch'}]

    assert response.status_code == 200
    parsed_response = sorted(parsed_response, key=lambda k: k['url'])
    expected = sorted(expected, key=lambda k: k['url'])
    for expected_token, returned_token in zip(expected, parsed_response):
        for key, value in expected_token.items():
            assert value == returned_token[key]
        assert returned_token.get('owner') is not None
        assert returned_token.get('url') is not None


@pytest.mark.parametrize("method", ['patch', 'delete'])
def test_other_user(db, client, method):
    non_admin_auth1 = make_auth(db, 'non-admin-1', is_admin=False, is_blocked=False)
    non_admin_auth2 = make_auth(db, 'non-admin-2', is_admin=False, is_blocked=False)

    client.put('/api/urls/abc', query_string={'url': 'http://example.com', 'meta.author': 'me'},
               headers=non_admin_auth1)
    method = getattr(client, method)
    response = method('/api/urls/abc', query_string={}, headers=non_admin_auth2)
    expected = {'error': {'code': 'insufficient-permissions',
                          'description': 'You are not allowed to make this request'},
                'status': 403}

    assert response.status_code == 403
    assert response.get_json() == expected

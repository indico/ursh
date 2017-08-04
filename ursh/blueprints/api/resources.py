from uuid import UUID

from flask import Response, current_app, g
from flask_apispec import MethodResource, marshal_with, use_kwargs
from werkzeug.exceptions import BadRequest, Conflict, MethodNotAllowed, NotFound

from ursh import db
from ursh.models import URL, Token
from ursh.schemas import TokenSchema, URLSchema
from ursh.util.decorators import admin_only, authorize_request_for_url, marshal_many_or_one


class TokenResource(MethodResource):
    @admin_only
    @marshal_with(TokenSchema, code=201)
    @use_kwargs(TokenSchema)
    def post(self, **kwargs):
        if kwargs.get('name') is None:
            raise generate_bad_request('missing-args', 'New tokens need to mention the "name" attribute', args=['name'])
        if Token.query.filter_by(name=kwargs['name']).count() != 0:
            raise Conflict({'message': 'Token with name exists', 'args': ['name']})
        new_token = Token()
        populate_from_dict(new_token, kwargs, ('name', 'is_admin', 'is_blocked', 'callback_url'))
        db.session.add(new_token)
        db.session.commit()
        return new_token, 201

    @admin_only
    @marshal_with(TokenSchema(), code=200)
    @use_kwargs(TokenSchema)
    def patch(self, api_key=None, **kwargs):
        if not api_key:
            raise MethodNotAllowed
        try:
            UUID(api_key)
        except ValueError:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if token is None:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
        populate_from_dict(token, kwargs, ('is_admin', 'is_blocked', 'callback_url'))
        db.session.commit()
        return token

    @admin_only
    @use_kwargs(TokenSchema)
    def delete(self, api_key=None, **kwargs):
        if not api_key:
            raise MethodNotAllowed
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if token is not None:
            db.session.delete(token)
            db.session.commit()
            return Response(status=204)
        else:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})

    @admin_only
    @marshal_many_or_one(TokenSchema, 'api_key', code=200)
    @use_kwargs(TokenSchema)
    def get(self, api_key=None, **kwargs):
        if api_key is None:
            filter_params = ['name', 'is_admin', 'is_blocked', 'callback_url']
            filter_dict = {key: value for key, value in kwargs.items() if key in filter_params}
            tokens = Token.query.filter_by(**filter_dict)
            return tokens
        else:
            try:
                UUID(api_key)
            except ValueError:
                raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
            token = Token.query.filter_by(api_key=api_key).one_or_none()
            if not token:
                raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
            return token


class URLResource(MethodResource):
    @marshal_with(URLSchema(strict=True), code=201)
    @use_kwargs(URLSchema)
    def post(self, **kwargs):
        if not kwargs.get('url'):
            raise generate_bad_request('missing-args', 'URL missing', args=['url'])
        if kwargs.get('allow_reuse'):
            existing_url = URL.query.filter_by(url=kwargs.get('url')).one_or_none()
            if existing_url:
                return existing_url, 201
        new_url = create_new_url(data=kwargs)
        db.session.add(new_url)
        db.session.commit()

        return new_url, 201

    @use_kwargs(URLSchema)
    @authorize_request_for_url
    @marshal_with(URLSchema, code=201)
    def put(self, shortcut=None, **kwargs):
        existing_url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if existing_url:
            if kwargs.get('allow_reuse'):
                return existing_url, 201
            else:
                raise Conflict({'message': 'Shortcut already exists', 'args': ['shortcut']})
        new_url = create_new_url(data=kwargs, shortcut=shortcut)
        db.session.add(new_url)
        db.session.commit()
        return new_url, 201

    @use_kwargs(URLSchema)
    @authorize_request_for_url
    @marshal_with(URLSchema)
    def patch(self, shortcut=None, **kwargs):
        if not shortcut:
            raise MethodNotAllowed
        metadata = kwargs.get('metadata')
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if not url:
            raise NotFound({'message': 'Shortcut does not exist', 'args': ['shortcut']})
        url.custom_data = metadata
        populate_from_dict(url, kwargs, ('shortcut', 'url', 'allow_reuse'))
        db.session.commit()
        return url

    @authorize_request_for_url
    @use_kwargs(URLSchema)
    def delete(self, shortcut=None, **kwargs):
        if not shortcut:
            raise MethodNotAllowed
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if not url:
            raise NotFound({'message': 'Shortcut does not exist', 'args': ['shortcut']})
        db.session.delete(url)
        db.session.commit()
        return Response(status=204)

    @marshal_many_or_one(URLSchema, 'shortcut', code=200)
    @use_kwargs(URLSchema)
    @authorize_request_for_url
    def get(self, shortcut=None, **kwargs):
        if shortcut is None:
            metadata = kwargs.get('metadata')
            filters = []
            if kwargs.get('url'):
                filters.append(URL.url == kwargs.get('url'))
            if not g.token.is_admin or not kwargs.get('all'):
                filters.append(URL.token == g.token)
            if metadata:
                filters.append(URL.custom_data.contains(metadata))
            return URL.query.filter(*filters).all()
        else:
            url = URL.query.filter_by(shortcut=shortcut).one_or_none()
            if not url:
                raise NotFound({'message': 'Shortcut does not exist', 'args': ['shortcut']})
            return url


def populate_from_dict(obj, values, fields):
    for field in fields:
        if field in values:
            setattr(obj, field, values[field])


def create_new_url(data, shortcut=None):
    metadata = data.get('metadata')
    if not metadata:
        metadata = {}
    if shortcut in current_app.config.get('BLACKLISTED_URLS'):
        raise generate_bad_request('invalid-shortcut', 'Invalid shortcut',
                                   args=['shortcut'])
    new_url = URL(token=g.token, custom_data=metadata, shortcut=shortcut)
    populate_from_dict(new_url, data, ('url', 'allow_reuse'))
    return new_url


def generate_bad_request(error_code, message, **kwargs):
    message_dict = {'code': error_code,
                    'description': message}
    message_dict.update(kwargs)
    return BadRequest(message_dict)

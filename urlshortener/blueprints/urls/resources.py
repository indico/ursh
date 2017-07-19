import re

from flask import Response, g
from flask_apispec import MethodResource, marshal_with, use_kwargs
from werkzeug.exceptions import BadRequest, Conflict, MethodNotAllowed

from urlshortener import db
from urlshortener.models import URL, Token
from urlshortener.schemas import TokenSchema, URLSchema
from urlshortener.util.decorators import admin_only, authorize_request_for_url, marshal_many_or_one


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
        if not validate_callback_url(kwargs.get('callback_url')):
            raise generate_bad_request('missing-args', 'Callback URL is invalid', args=['callback_url'])
        populate_from_dict(new_token, kwargs, ('name', 'is_admin', 'is_blocked', 'callback_url'))
        db.session.add(new_token)
        db.session.commit()

        return new_token, 201

    @admin_only
    @marshal_with(TokenSchema(), code=200)
    @use_kwargs(TokenSchema)
    def patch(self, api_key, **kwargs):
        if not api_key:
            raise MethodNotAllowed
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if validate_callback_url(kwargs.get('callback_url')):
            raise generate_bad_request('missing-args', 'Callback URL is invalid', args=['callback_url'])
        populate_from_dict(token, kwargs, ('is_admin', 'is_blocked', 'callback_url'))
        db.session.commit()
        return token

    @admin_only
    @use_kwargs(TokenSchema)
    def delete(self, api_key, **kwargs):
        if not api_key:
            raise MethodNotAllowed
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if token is not None:
            db.session.delete(token)
            db.session.commit()
            return Response(status=204)
        else:
            return Response(status=404)

    @admin_only
    @marshal_many_or_one(TokenSchema, 'api_key', code=200)
    @use_kwargs(TokenSchema)
    def get(self, api_key, **kwargs):
        if api_key is None:
            filter_params = ['name', 'is_admin', 'is_blocked']
            filter_dict = {key: value for key, value in kwargs.items() if key in filter_params}
            tokens = Token.query.filter_by(**filter_dict)
            return tokens
        else:
            token = Token.query.filter_by(api_key=api_key).one_or_none()
            if not token:
                return Response(status=404)
            return token


class URLResource(MethodResource):
    @marshal_with(URLSchema(strict=True), code=201)
    @use_kwargs(URLSchema)
    def post(self, **kwargs):
        if kwargs.get('url') is None:
            raise generate_bad_request('missing-args', 'URL invalid or missing',
                                       args=['url'])
        if kwargs['shortcut']:
            return Response(status=404)
        new_url = create_new_url(data=kwargs)
        db.session.add(new_url)
        db.session.commit()

        return new_url, 201

    @use_kwargs(URLSchema)
    @authorize_request_for_url
    @marshal_with(URLSchema(strict=True), code=201)
    def put(self, shortcut, **kwargs):
        if not kwargs.get('url'):
            raise generate_bad_request('missing-args', 'URL invalid or missing',
                                       args=['url'])
        existing_url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if existing_url:
            if kwargs.get('allow_reuse'):
                return existing_url
            else:
                raise Conflict({'message': 'Shortcut already exists', 'args': ['shortcut']})
        new_url = create_new_url(data=kwargs, shortcut=shortcut)
        db.session.add(new_url)
        db.session.commit()

        return new_url, 201

    @use_kwargs(URLSchema)
    @authorize_request_for_url
    @marshal_with(URLSchema)
    def patch(self, shortcut, **kwargs):
        if not shortcut:
            raise MethodNotAllowed
        metadata = kwargs.get('metadata')
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if not url:
            return Response(status=404)
        url.custom_data = metadata
        populate_from_dict(url, kwargs, ('shortcut', 'url', 'allow_reuse'))
        db.session.commit()
        return url

    @use_kwargs(URLSchema)
    @authorize_request_for_url
    def delete(self, shortcut, **kwargs):
        if not shortcut:
            raise MethodNotAllowed
        url = URL.query.filter_by(shortcut=shortcut).first_or_404()
        db.session.delete(url)
        db.session.commit()
        return Response(status=204)

    @use_kwargs(URLSchema)
    @authorize_request_for_url
    @marshal_many_or_one(URLSchema, 'shortcut')
    def get(self, shortcut=None, **kwargs):
        if shortcut is None:
            metadata = kwargs.get('metadata')
            filters = []
            if not g.token.is_admin or not kwargs.get('all'):
                filters = [URL.token == g.token]
            if metadata:
                filters.append(URL.custom_data.contains(metadata))
            return URL.query.filter(*filters).all()
        else:
            return URL.query.filter_by(shortcut=shortcut).first_or_404()


def populate_from_dict(obj, values, fields):
    for field in fields:
        if field in values:
            setattr(obj, field, values[field])


def create_new_url(data, shortcut=None):
    metadata = data.get('metadata')
    print(metadata)
    if not metadata:
        metadata = {}
    new_url = URL(token=g.token, custom_data=metadata, shortcut=shortcut)
    populate_from_dict(new_url, data, ('url', 'allow_reuse'))
    return new_url


def generate_bad_request(error_code, message, **kwargs):
    message_dict = {'code': error_code,
                    'description': message}
    message_dict.update(kwargs)
    return BadRequest(message_dict)


def validate_callback_url(url):
    regex = re.compile(r'^https?://[^/:]+(:[0-9]+)?(/.*)?$')
    return url is None or regex.match(url) is not None

from flask import Response, request
from flask_apispec import MethodResource, marshal_with, use_kwargs
from werkzeug.exceptions import BadRequest

from urlshortener import db
from urlshortener.models import URL, Token
from urlshortener.schemas import TokenSchema, URLSchema
from urlshortener.util.decorators import admin_only, authorize_request_for_url, marshal_many_or_one


class TokenResource(MethodResource):

    @marshal_with(TokenSchema, code=201)
    @use_kwargs(TokenSchema)
    @admin_only
    def post(self, **kwargs):
        if kwargs.get('name') is None:
            raise BadRequest
        new_token = Token()
        populate_from_dict(new_token, kwargs, ('name', 'is_admin', 'is_blocked', 'callback_url'))
        db.session.add(new_token)
        db.session.commit()

        return new_token, 201

    @marshal_with(TokenSchema(), code=200)
    @use_kwargs(TokenSchema)
    @admin_only
    def patch(self, api_key, **kwargs):
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        populate_from_dict(token, kwargs, ('is_admin', 'is_blocked', 'callback_url'))
        db.session.commit()
        return token

    @use_kwargs(TokenSchema)
    @admin_only
    def delete(self, api_key, **kwargs):
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if token is not None:
            db.session.delete(token)
            db.session.commit()
            return Response(status=204)
        else:
            return Response(status=404)

    @marshal_many_or_one(TokenSchema, 'api_key', code=200)
    @use_kwargs(TokenSchema)
    @admin_only
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
    @marshal_with(URLSchema, code=201)
    @use_kwargs(URLSchema)
    def post(self, **kwargs):
        if kwargs.get('url') is None:
            raise BadRequest
        if kwargs['shortcut']:
            return Response(status=404)
        return create_new_url(data=kwargs), 201

    @marshal_with(URLSchema, code=201)
    @use_kwargs(URLSchema)
    @authorize_request_for_url
    def put(self, shortcut, **kwargs):
        if kwargs['url'] is None:
            raise BadRequest
        return create_new_url(data=kwargs, shortcut=shortcut), 201

    @use_kwargs(URLSchema)
    @marshal_with(URLSchema)
    @authorize_request_for_url
    def patch(self, shortcut, **kwargs):
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
        # TODO: Handle missing args
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if url is not None:
            db.session.delete(url)
            db.session.commit()
            return Response(status=204)
        else:
            return Response(status=404)

    @marshal_many_or_one(URLSchema, 'shortcut')
    @use_kwargs(URLSchema)
    @authorize_request_for_url
    def get(self, shortcut=None, **kwargs):
        if shortcut is None:
            metadata = kwargs.get('metadata')
            filters = [URL.token == request.token]
            if request.token.is_admin and kwargs.get('all'):
                filters = []
            if metadata:
                filters.append(URL.custom_data.contains(metadata))
            return db.session.query(URL).filter(*filters).all()
        else:
            url = URL.query.filter_by(shortcut=shortcut).one_or_none()
            if not url:
                return Response(status=404)
            return url


def populate_from_dict(obj, values, fields):
    for field in fields:
        if field in values:
            setattr(obj, field, values[field])


def create_new_url(data=None, shortcut=None):
    metadata = data.get('metadata')
    if not metadata:
        metadata = {}
    new_url = URL(token=request.token, custom_data=metadata, shortcut=shortcut)
    populate_from_dict(new_url, data, ('url', 'allow_reuse'))
    db.session.add(new_url)
    db.session.commit()

    return new_url

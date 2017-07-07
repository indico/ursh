import json

from flask import Response
from flask_apispec import MethodResource, marshal_with, use_kwargs

from urlshortener import db
from urlshortener.models import Token, URL
from urlshortener.schemas import TokenSchema, URLSchema
from urlshortener.util.decorators import admin_only, authorize_request, marshal_many_or_one, authorize_request_for_url


class TokenResource(MethodResource):

    @marshal_with(TokenSchema, 201)
    @use_kwargs(TokenSchema)
    @admin_only
    def post(self, **kwargs):
        # TODO: detailed error handling
        if kwargs['name'] is None:
            return Response(status=400)
        new_token = Token()
        print(f'field: {field}')
        for field in ('name', 'is_admin', 'is_blocked', 'callback_url'):
            if field in kwargs:
                setattr(new_token, field, kwargs[field])
        db.session.add(new_token)
        db.session.commit()

        return new_token, 201

    @marshal_with(TokenSchema(), code=200)
    @use_kwargs(TokenSchema)
    @admin_only
    def patch(self, **kwargs):
        # TODO: Handle missing args
        token = Token.query.filter_by(api_key=kwargs['api_key']).one_or_none()
        for field in ('is_admin', 'is_blocked', 'callback_url'):
            if field in kwargs:
                setattr(token, field, kwargs[field])
        db.session.commit()
        return token

    @use_kwargs(TokenSchema)
    @admin_only
    def delete(self, api_key, **kwargs):
        # TODO: Handle missing args
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
    def get(self, api_key=None, **kwargs):
        # TODO: Handle missing args
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

    @marshal_with(URLSchema, 201)
    @use_kwargs(URLSchema)
    @authorize_request
    def post(self, **kwargs):
        if kwargs['url'] is None:
            return Response(status=400)
        new_url = URL()
        for field in ('url', 'metadata', 'allow_reuse'):
            if field in kwargs:
                setattr(new_url, field, kwargs[field])
        db.session.add(new_url)
        db.session.commit()

        return new_url, 201

    @use_kwargs(URLSchema, 201)
    def put(self, shortcut, **kwargs):
        if kwargs['url'] is None:
            return Response(status=400)
        new_url = URL()
        for field in ('shortcut', 'url', 'metadata', 'allow_reuse'):
            if field in kwargs:
                setattr(new_url, field, kwargs[field])
        db.session.add(new_url)
        db.session.commit()

        return new_url, 201

    @use_kwargs(URLSchema)
    def patch(self, shortcut):
        pass

    @use_kwargs(URLSchema)
    @authorize_request_for_url
    def delete(self, shortcut):
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
            if metadata:
                metadata = json.loads(metadata)
                query = []
                for key, value in metadata.items():
                    query.append(URL.custom_data[key].astext == value)
            urls = db.session.query(URL).filter(*query).all()
            return urls
        else:
            url = URL.query.filter_by(shortcut=shortcut).one_or_none()
            if not url:
                return Response(status=404)
            return url

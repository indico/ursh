from flask_apispec import use_kwargs, marshal_with, MethodResource
from flask import Response
from marshmallow import fields
from sqlalchemy.exc import SQLAlchemyError

from urlshortener import db
from urlshortener.models import URL, Token
from urlshortener.schemas import TokenSchema, URLSchema
from urlshortener.util.decorators import authorize_request, admin_only, marshal_many_or_one


class TokenResource(MethodResource):

    @marshal_with(TokenSchema, code=203)
    @use_kwargs(TokenSchema)
    @admin_only
    def post(self, **kwargs):
        if kwargs['name'] is None:
            return Response(status=400)
        # try:
        new_token = Token()
        new_token.name = kwargs['name']
        new_token.is_blocked = kwargs.get('is_blocked')
        new_token.is_admin = kwargs.get('is_admin')
        new_token.callback_url = kwargs.get('callback_url')
        db.session.add(new_token)
        # db.session.commit()
        return new_token
            # TODO: detailed error handling
            # except KeyError:
            #     return Response(status=400)
            # except SQLAlchemyError:
            #     return Response(status=400)

    @marshal_with(TokenSchema(), code=200)
    @use_kwargs(TokenSchema())
    @admin_only
    def patch(self, **kwargs):
        try:
            token = Token.query.filter_by(api_key=kwargs['api_key'])
            token.is_admin = kwargs.get('is_admin', token.is_admin)
            token.is_blocked = kwargs.get('is_blocked', token.is_blocked)
            token.callback_url = kwargs.get('callback_url', token.callback_url)
            db.session.commit()
        except SQLAlchemyError:
            return Response(status=400)

        return token

    @admin_only
    def delete(self, api_key):
        try:
            token = Token.query.filter(api_key=api_key)
            token.delete()
            return Response(status=204)
        except SQLAlchemyError:
            return Response(status=400)

    @marshal_many_or_one(TokenSchema, 'api_key', code=200)
    @use_kwargs(TokenSchema)
    @admin_only
    def get(self, api_key=None, **kwargs):
        print(f'HERE: {api_key}, {kwargs}')
        if api_key is None:
            tokens = Token.query.all()
            print(f'these are the tokens: {tokens}')
            return tokens
        else:
            token = Token.query.filter_by(api_key=api_key)[0]
            print(f'i am of type{type(token)}')
            if not token:
                return Response(status=404)
            return token


class URLResource(MethodResource):

    @use_kwargs(URLSchema())
    @authorize_request
    def post(self, shortcut):
        pass

    @use_kwargs(URLSchema())
    def put(self, shortcut):
        pass

    @use_kwargs(URLSchema())
    def patch(self, shortcut):
        pass

    @use_kwargs(URLSchema())
    def delete(self, shortcut):
        pass

    @use_kwargs(URLSchema())
    def get(self, shortcut):
        if shortcut is None:
            pass
        else:
            pass
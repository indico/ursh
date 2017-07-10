from datetime import datetime, timezone
from functools import wraps

from flask import Response
from flask_apispec import marshal_with

from urlshortener import db
from urlshortener.models import URL, Token


def authorize_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        print('authorizing....')
        token = Token.query.filter_by(api_key=kwargs['auth_token']).one_or_none()
        if token is None or token.is_blocked:
            return Response(status=401)
        token.token_uses += 1
        token.last_access = datetime.now(timezone.utc)
        db.session.commit()
        kwargs['token'] = token
        return f(*args, **kwargs)
    return wrapper


def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        authorized_function = authorize_request(f)(*args, **kwargs)
        token = Token.query.filter_by(api_key=kwargs['auth_token']).one_or_none()
        if token and not token.is_admin:
            return Response(status=403)
        else:
            return authorized_function
    return wrapper


def marshal_many_or_one(cls, param, **decorator_args):
    def marshal(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if kwargs[param] is None:
                return marshal_with(cls(many=True), **decorator_args)(f)(*args, **kwargs)
            else:
                return marshal_with(cls, **decorator_args)(f)(*args, **kwargs)
        return wrapper
    return marshal


def authorize_request_for_url(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = Token.query.filter_by(api_key=kwargs['auth_token']).one_or_none()
        if token is None or token.is_blocked:
            return Response(status=401)
        token.token_uses += 1
        token.last_access = datetime.now(timezone.utc)
        db.session.commit()

        shortcut = kwargs['shortcut']
        if shortcut:
            url = URL.query.filter_by(shortcut=shortcut).one_or_none()
            if url:
                if not url.token == token and not token.is_admin:
                    return Response(status=403)

        kwargs['token'] = token
        return f(*args, **kwargs)
    return wrapper

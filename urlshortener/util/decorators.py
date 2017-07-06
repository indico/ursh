from flask import Response
from flask_apispec import marshal_with
from datetime import datetime, timezone

from urlshortener.models import Token
from urlshortener import db


def authorize_request(f):
    def wrapper(*args, **kwargs):
        try:
            token = Token.query.filter_by(api_key=kwargs['auth_token'])[0]
        except IndexError:
            return Response(status=401)
        token.token_uses += 1
        token.last_access = datetime.now(timezone.utc)
        db.session.commit()
        if token is None or token.is_blocked:
            return Response(status=401)
        else:
            return f(*args, **kwargs)
    return wrapper


def admin_only(f):
    def wrapper(*args, **kwargs):
        try:
            token = Token.query.filter_by(api_key=kwargs['auth_token'])[0]
        except IndexError:
            return Response(status=401)
        token.last_access = datetime.now(timezone.utc)
        db.session.commit()
        if not token.is_admin:
            return Response(status=403)
        else:
            return authorize_request(f)(*args, **kwargs)
    return wrapper


def marshal_many_or_one(cls, param, **decorator_args):
    def marshal(f):
        def wrapper(*args, **kwargs):
            if kwargs[param] is None:
                return marshal_with(cls(many=True), **decorator_args)(f)(*args, **kwargs)
            else:
                return marshal_with(cls, **decorator_args)(f)(*args, **kwargs)
        return wrapper
    return marshal

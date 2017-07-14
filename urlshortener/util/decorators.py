from functools import wraps

from flask import g, jsonify
from flask_apispec import marshal_with

from urlshortener.models import URL


def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.token and not g.token.is_admin:
            return jsonify({'status': 403,
                            'error': {'code': 'insufficient-permissions',
                                      'message': 'You are not allowed to make this request'}}), 403
        else:
            return f(*args, **kwargs)
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
        shortcut = kwargs['shortcut']
        if shortcut:
            url = URL.query.filter_by(shortcut=shortcut).one_or_none()
            if url and url.token != g.token and not g.token.is_admin:
                return jsonify({'status': 403,
                                'error': {'code': 'insufficient-permissions',
                                          'message': 'You are not allowed to make this request'}}), 403
        return f(*args, **kwargs)
    return wrapper

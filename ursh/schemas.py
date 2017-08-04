import json

from flask import current_app
from flask_marshmallow import Schema
from marshmallow import fields, pre_dump
from werkzeug.exceptions import BadRequest, HTTPException
from werkzeug.routing import RequestRedirect
from werkzeug.urls import url_parse


SHORTCUT_ALPHABET = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVW1234567890-')


class TokenSchema(Schema):
    auth_token = fields.Str(load_only=True, location='headers')
    api_key = fields.Str()
    name = fields.Str()
    is_admin = fields.Boolean()
    is_blocked = fields.Boolean()
    token_uses = fields.Int()
    last_access = fields.DateTime()
    callback_url = fields.URL()

    class Meta:
        strict = True

    def handle_error(self, error, data):
        if type(data) == dict:
            raise BadRequest({'code': 'validation-error', 'args': sorted(error.field_names),
                              'messages': error.messages})


class URLSchema(Schema):
    auth_token = fields.Str(load_only=True, location='headers')
    shortcut = fields.Str(validate=lambda x: validate_shortcut(x), location='view_args')
    url = fields.URL()
    metadata = fields.Dict()
    token = fields.Str(load_from='token.api_key')
    allow_reuse = fields.Boolean(load_only=True, default=False)
    all = fields.Boolean(load_only=True, default=False)

    class Meta:
        strict = True

    @pre_dump
    def prepare_obj(self, data):
        data = {
            'url': data.url,
            'shortcut': data.shortcut,
            'metadata': json.dumps(data.custom_data),
            'token': data.token.api_key,
        }
        return data

    def handle_error(self, error, data):
        if type(data) == dict:
            raise BadRequest({'code': 'validation-error', 'args': sorted(error.field_names),
                              'messages': error.messages})


def validate_shortcut(shortcut):
    return not endpoint_for_url(shortcut) and set(shortcut) <= SHORTCUT_ALPHABET and \
           shortcut not in current_app.config.get('BLACKLISTED_URLS')


def endpoint_for_url(url):
    urldata = url_parse(url)
    adapter = current_app.url_map.bind(urldata.netloc)
    try:
        match = adapter.match(urldata.path)
        return not match[0].startswith('redirection')
    except RequestRedirect as e:
        return endpoint_for_url(e.new_url)
    except HTTPException:
        return False

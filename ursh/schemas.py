import json

from flask_marshmallow import Schema
from marshmallow import fields, pre_dump
from werkzeug.exceptions import BadRequest


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
            raise BadRequest({'code': 'validation-error', 'args': error.field_names,
                              'messages': error.messages})


class URLSchema(Schema):
    auth_token = fields.Str(load_only=True, location='headers')
    shortcut = fields.Str()
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
            raise BadRequest({'code': 'validation-error', 'args': error.field_names,
                              'messages': error.messages})


def validate_shortcut(shortcut):
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVW1234567890'
    for letter in shortcut:
        if letter not in alphabet:
            return False
    return True

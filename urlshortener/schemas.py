import json

from flask_marshmallow import Schema
from marshmallow import fields, post_load, pre_dump

from urlshortener.models import URL, Token


class TokenSchema(Schema):
    auth_token = fields.Str(required=True, load_only=True, location='headers')
    api_key = fields.Str(required=True)
    name = fields.Str()
    is_admin = fields.Boolean()
    is_blocked = fields.Boolean()
    token_uses = fields.Int()
    last_access = fields.DateTime()

    @post_load
    def make(self, data):
        return Token(**data)


class URLSchema(Schema):
    auth_token = fields.Str(required=True, load_only=True, location='headers')
    shortcut = fields.Str(required=True)
    url = fields.URL()
    metadata = fields.Dict(load_from='custom_data')
    token = fields.Str(required=True, load_from='token.api_key')
    allow_reuse = fields.Boolean(load_only=True, default=False)
    all = fields.Boolean(load_only=True, default=False)

    @pre_dump
    def prepare_obj(self, data):
        data = {
            'url': data.url,
            'shortcut': data.shortcut,
            'metadata': json.dumps(data.custom_data),
            'token': data.token.api_key,
        }
        return data

    @post_load
    def make(self, data):
        return URL(**data)

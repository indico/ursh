import json
import re

from marshmallow import fields, post_load, pre_load, pre_dump
from flask_marshmallow import Schema

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
    metadata = fields.Str(load_from='custom_data')
    token = fields.Str(required=True, load_from='token.api_key')
    allow_reuse = fields.Boolean()

    @pre_load
    def move_metadata(self, data):
        """
        Move all the metadata.x style query parameters into one field
        called "metadata", which has a JSON string with all the metadata
        parameters as the value.
        """
        metadata = data.get('metadata')
        if metadata:
            data['metadata'] = json.dumps(metadata)

        return data

    @pre_dump
    def prepare_obj(self, data):
        data = {
            'url': data.url,
            'shortcut': data.shortcut,
            'metadata': data.custom_data,
            'token': data.token.api_key,
            'allow_reuse': data.allow_reuse
        }
        return data

    @post_load
    def make(self, data):
        return URL(**data)

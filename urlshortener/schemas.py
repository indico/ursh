import re
import json

from marshmallow import Schema, fields, pre_load, post_load

from urlshortener.models import Token, URL


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
    auth_token = fields.Str(required=True, load_only=True)
    shortcut = fields.Str(required=True)
    url = fields.URL()
    metadata = fields.Str(dump_to='custom_data')
    token = fields.Str(required=True)

    @pre_load
    def move_metadata(self, data):
        """
        Move all the metadata.x style query parameters into one field
        called "metadata", which has a JSON string with all the metadata
        parameters as the value.
        """
        metadata = {}
        reformatted_data = {'metadata': metadata}
        for key in data.keys():
            m = re.match(r'metadata\.(.*)', key)
            if m is not None:
                metadata_key = m.group(1)
                metadata[metadata_key] = data[key]
            else:
                reformatted_data[key] = data[key]
        reformatted_data['metadata'] = json.dumps(metadata)

    @post_load
    def make(self, data):
        return URL(**data)

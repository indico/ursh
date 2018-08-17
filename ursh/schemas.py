import json
import posixpath

from flask import current_app
from flask_marshmallow import Schema
from marshmallow import ValidationError, fields, pre_dump, validates
from werkzeug.exceptions import BadRequest, HTTPException
from werkzeug.routing import RequestRedirect
from werkzeug.urls import url_parse

from ursh.models import ALPHABET_MANUAL, ALPHABET_RESTRICTED


def validate_shortcut(shortcut, restricted):
    alphabet = ALPHABET_RESTRICTED if restricted else ALPHABET_MANUAL
    return (not endpoint_for_url(shortcut)
            and set(shortcut) <= set(alphabet)
            and shortcut not in current_app.config['BLACKLISTED_URLS'])


class SchemaBase(Schema):
    class Meta:
        strict = True

    @staticmethod
    def handle_error(error, data):
        raise BadRequest({'code': 'validation-error', 'args': sorted(error.field_names), 'messages': error.messages})


class TokenSchema(SchemaBase):
    """Schema class to validate tokens."""

    auth_token = fields.Str(load_only=True, location='headers')
    api_key = fields.Str()
    name = fields.Str()
    is_admin = fields.Boolean()
    is_blocked = fields.Boolean()
    token_uses = fields.Int()
    last_access = fields.DateTime()
    callback_url = fields.URL()


class URLSchema(SchemaBase):
    """Schema class to validate URLs.

    Note: use one of the sub-classes below for validation, depending on the shortcut requirements.
    """

    auth_token = fields.Str(load_only=True, location='headers')
    shortcut = fields.Str(location='view_args')
    host = fields.URL()
    url = fields.URL()
    short_url = fields.URL()
    metadata = fields.Dict()
    token = fields.Str(load_from='token.api_key')
    allow_reuse = fields.Boolean(load_only=True, default=False)
    all = fields.Boolean(load_only=True, default=False)

    @pre_dump
    def prepare_obj(self, data):
        data = {
            'url': data.url,
            'short_url': posixpath.join(current_app.config['REDIRECTION_HOST'], data.shortcut),
            'metadata': json.dumps(data.custom_data),
            'token': data.token.api_key,
        }
        return data


class URLSchemaManual(URLSchema):
    """Validator for user-specified shortcuts (i.e. all requests except POST)."""

    @validates('shortcut')
    def validate_shortcut(self, data):
        if not validate_shortcut(data, restricted=False):
            raise ValidationError('Invalid value.')


class URLSchemaRestricted(URLSchema):
    """Validator for auto-generated shortcuts (i.e. POST requests)."""

    @validates('shortcut')
    def validate_shortcut(self, data):
        if not validate_shortcut(data, restricted=True):
            raise ValidationError('Invalid value.')


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

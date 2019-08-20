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
    def handle_error(error, data, **kwargs):
        raise BadRequest({'code': 'validation-error', 'messages': error.messages})


class TokenSchema(SchemaBase):
    """Schema class to validate tokens."""
    api_key = fields.Str(description='The token API key - uniquely identifies the token')
    name = fields.Str(description='The token name')
    is_admin = fields.Boolean(description='Is this an admin token?')
    is_blocked = fields.Boolean(description='Is this token blocked?')
    token_uses = fields.Int(description='How many times has this token been used?')
    last_access = fields.DateTime(description='Last time this token was used')
    callback_url = fields.URL(description='A request will be made to this URL every time the token is used')


class URLSchema(SchemaBase):
    """Schema class to validate URLs.

    Note: use one of the sub-classes below for validation, depending on the shortcut requirements.
    """
    shortcut = fields.Str(location='view_args', description='The generated or manually set URL shortcut')
    url = fields.URL(description='The original URL (the short URL target)')
    short_url = fields.URL(description='The short URL')
    metadata = fields.Dict(description='Additional metadata (provided upon short URL creation)')
    owner = fields.Str(load_from='token.name', description='The name of the token than created the short URL')
    allow_reuse = fields.Boolean(load_only=True, default=False)

    @pre_dump
    def prepare_obj(self, data, **kwargs):
        data = {
            'url': data.url,
            'shortcut': data.shortcut,
            'short_url': posixpath.join(current_app.config['REDIRECTION_HOST'], data.shortcut),
            'metadata': data.custom_data,
            'owner': data.token.name,
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

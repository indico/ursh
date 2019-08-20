from uuid import UUID

from flask import Response, current_app, g
from flask_apispec import MethodResource, marshal_with, use_kwargs
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, Conflict, MethodNotAllowed, NotFound

from ursh import db
from ursh.models import URL, Token
from ursh.schemas import TokenSchema, URLSchemaManual, URLSchemaRestricted
from ursh.util.decorators import admin_only, authorize_request_for_url, marshal_many_or_one


class TokenResource(MethodResource):
    """Handle token-related requests.
    ---
    options:
      tags:
      - users
      summary: responds with the allowed HTTP methods
      parameters:
      - in: header
        name: Authorization
        description: the API key bearer
        type: string
        format: uuid
        required: true
      responses:
        200:
          description: OK
        401:
          description: not authorized
    """
    @admin_only
    @marshal_with(TokenSchema, code=201)
    @use_kwargs(TokenSchema)
    def post(self, **kwargs):
        """Create a new token.
        ---
        tags:
        - admins
        summary: creates a new token
        description: >
          Create a new API token for communicating with the API.
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: body
          name: token
          description: the token to create
          required: true
          schema:
            type: object
            required:
              - name
            properties:
              name:
                type: string
                example: newTokenName
                description: the new token name
              is_admin:
                type: boolean
                description: 'whether to create an admin token'
              is_blocked:
                type: boolean
                description: 'whether the new token must be blocked'
              callback_url:
                type: string
                format: url
                description: 'a callback URL for the new token'
                example: 'https://cern.ch'
        responses:
          200:
            description: token created successfully
            schema:
              $ref: '#/components/schemas/Token'
          400:
            description: token `name` missing
        """
        if not kwargs.get('name'):
            raise generate_bad_request('missing-args', 'New tokens need to mention the "name" attribute', args=['name'])
        if Token.query.filter_by(name=kwargs['name']).count() != 0:
            raise Conflict({'message': 'Token with name exists', 'args': ['name']})
        new_token = Token()
        populate_from_dict(new_token, kwargs, ('name', 'is_admin', 'is_blocked', 'callback_url'))
        db.session.add(new_token)
        db.session.commit()
        current_app.logger.info('Token created by %s: %s (admin: %s)', g.token.name, new_token.name, new_token.is_admin)
        return new_token, 201

    @admin_only
    @marshal_with(TokenSchema, code=200)
    @use_kwargs(TokenSchema)
    def patch(self, api_key=None, **kwargs):
        """Modify an existing token.
        ---
        tags:
        - admins
        summary: modifies an existing token
        operationId: patchToken
        description: >
          Modify the properties of an existing API token.
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: path
          name: api_key
          description: the API key of the token to modify
          required: true
          type: string
          format: uuid
        - in: body
          name: updated values
          description: the new values of the token; one or more can be specified
          schema:
            type: object
            required:
              - name
            properties:
              is_admin:
                type: boolean
                description: 'change token admin status'
              is_blocked:
                type: boolean
                description: 'change token blocked status'
              callback_url:
                type: string
                format: url
                description: 'change token callback URL'
                example: 'https://cern.ch'
        responses:
          200:
            description: token modified successfully
            schema:
              $ref: '#/components/schemas/Token'
          404:
            description: token to modify not found
          405:
            description: 'method not allowed: `api_key` not specified'
        """
        if not api_key:
            raise MethodNotAllowed
        try:
            UUID(api_key)
        except ValueError:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if not token:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
        populate_from_dict(token, kwargs, ('is_admin', 'is_blocked', 'callback_url'))
        db.session.commit()
        current_app.logger.info('Token updated by %s: %s (%r)', g.token.name, token.name, kwargs)
        return token

    @admin_only
    @use_kwargs(TokenSchema)
    def delete(self, api_key=None, **kwargs):
        """Delete an existing token.
        ---
        tags:
        - admins
        summary: deletes an existing token
        operationId: deleteToken
        description: >
          Delete an existing API token.
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: path
          name: api_key
          description: the API key of the token to delete
          required: true
          type: string
          format: uuid
        responses:
          204:
            description: token deleted successfully
          404:
            description: token to delete not found
          405:
            description: 'method not allowed: `api_key` not specified'
        """
        if not api_key:
            raise MethodNotAllowed
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if not token:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
        try:
            db.session.delete(token)
            db.session.commit()
        except IntegrityError:
            raise Conflict({'message': 'There are URLs associated with the token specified for deletion',
                            'args': ['api_key']})
        current_app.logger.info('Token deleted by %s: %s', g.token.name, token.name)
        return Response(status=204)

    @admin_only
    @marshal_many_or_one(TokenSchema, 'api_key', code=200)
    @use_kwargs(TokenSchema)
    def get(self, api_key=None, **kwargs):
        """Obtain one or more tokens.
        ---
        tags:
        - admins
        summary: returns one or more tokens
        operationId: getToken
        description: >
          Obtain the API tokens that match the given parameters. If `api_key` is provided,
          then exactly one token will be returned. Otherwise, a collection of tokens that
          match the provided parameters will be returned (maybe empty).
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: path
          name: api_key
          description: the API key of the token to obtain - may be omitted
          type: string
          format: uuid
        - in: body
          name: filters
          description: the token filters to apply
          schema:
            type: object
            properties:
              name:
                type: string
                example: tokenName
              is_admin:
                type: boolean
              is_blocked:
                type: boolean
              callback_url:
                type: string
                format: url
                example: https://cern.ch
        responses:
          200:
            description: return a collection of the found tokens
            schema:
              format: array
              items:
                $ref: '#/components/schemas/Token'
          404:
            description: 'no token found for the specified `api_key`'
        """
        if not api_key:
            filter_params = ['name', 'is_admin', 'is_blocked', 'callback_url']
            filter_dict = {key: value for key, value in kwargs.items() if key in filter_params}
            tokens = Token.query.filter_by(**filter_dict)
            return tokens
        try:
            UUID(api_key)
        except ValueError:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
        token = Token.query.filter_by(api_key=api_key).one_or_none()
        if not token:
            raise NotFound({'message': 'API key does not exist', 'args': ['api_key']})
        return token


class URLResource(MethodResource):
    """
    ---
    options:
      tags:
      - users
      summary: responds with the allowed HTTP methods
      parameters:
      - in: header
        name: Authorization
        description: the API key bearer
        type: string
        format: uuid
        required: true
      responses:
        200:
          description: OK
        401:
          description: not authorized
    """
    @marshal_with(URLSchemaRestricted, code=201)
    @use_kwargs(URLSchemaRestricted)
    def post(self, **kwargs):
        """Create a new URL object.
        ---
        tags:
        - admins
        - users
        summary: generates a new URL shortcut
        operationId: createURL
        description: >
          Create a (new) shortcut for the given URL.
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: body
          name: URL properties
          description: the properties of the URL to create
          required: true
          schema:
            type: object
            required:
              - url
            properties:
              url:
                type: string
                format: url
                example: 'https://my.original.long.url/that/i-want/to/shorten'
                description: the original URL
              meta:
                type: object
                example: {
                  'a': 'foo',
                  'b': 'bar'
                }
              allow_reuse:
                type: boolean
                description: >
                  If a shortcut for the given URL already exists, then don't create a new one,
                  but return the existing short URL.
        responses:
          201:
            description: shortcut for URL created successfully
            schema:
              $ref: '#/components/schemas/URL'
          400:
            description: 'Bad Request: invalid `shortcut` value'
        """
        if not kwargs.get('url'):
            raise generate_bad_request('missing-args', 'URL missing', args=['url'])
        if kwargs.get('allow_reuse'):
            existing_url = URL.query.filter_by(url=kwargs.get('url'), is_custom=False).order_by(URL.shortcut).first()
            if existing_url:
                return existing_url, 201
        new_url = create_new_url(data=kwargs)
        db.session.add(new_url)
        db.session.commit()
        current_app.logger.info('URL created by %s: %s -> <%s> (%r)', g.token.name, new_url.shortcut, new_url.url,
                                kwargs.get('meta', {}))
        return new_url, 201

    @use_kwargs(URLSchemaManual)
    @authorize_request_for_url
    @marshal_with(URLSchemaManual, code=201)
    def put(self, shortcut=None, **kwargs):
        """Put a new URL object.
        ---
        tags:
        - admins
        - users
        summary: creates a manually specified URL shortcut
        operationId: putURL
        description: >
          Manually create a URL shortcut.
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: path
          name: shortcut
          description: the shortcut of the URL to put
          required: true
          type: string
        - in: body
          name: URL properties
          description: the properties of the URL to put
          required: true
          schema:
            type: object
            required:
              - url
            properties:
              url:
                type: string
                format: url
                example: 'https://my.original.long.url/that/i-want/to/shorten'
                description: the original URL
              meta:
                type: object
                example: {
                  'a': 'foo',
                  'b': 'bar'
                }
              allow_reuse:
                type: boolean
                description: >
                  If a shortcut for the given URL already exists, then don't create a new one,
                  but return the existing short URL; otherwise fail (see `409` status below).
        responses:
          201:
            description: shortcut for URL put successfully
            schema:
              $ref: '#/components/schemas/URL'
          400:
            description: 'Bad Request: the specified shortcut is invalid'
          409:
            description: 'shortcut already exists and `allow_reuse=true` was not specified'
        """
        existing_url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if existing_url:
            if kwargs.get('allow_reuse') and existing_url.url == kwargs['url']:
                return existing_url, 201
            else:
                raise Conflict({'message': 'This shortcut already exists',
                                'args': ['shortcut']})
        new_url = create_new_url(data=kwargs, shortcut=shortcut)
        db.session.add(new_url)
        db.session.commit()
        current_app.logger.info('URL created by %s: %s -> <%s> (%r)', g.token.name, new_url.shortcut, new_url.url,
                                kwargs.get('meta', {}))
        return new_url, 201

    @use_kwargs(URLSchemaManual)
    @authorize_request_for_url
    @marshal_with(URLSchemaManual)
    def patch(self, shortcut=None, **kwargs):
        """Modify an existing URL object.
        ---
        tags:
        - admins
        - users
        summary: modify an existing URL
        operationId: patchURL
        description: >
          Modify the properties of an existing URL object.
          Non-admin users may only patch their own URLs (created with their API key).
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: path
          name: shortcut
          description: the shortcut of the URL object to patch
          required: true
          type: string
        - in: body
          name: updated values
          description: the new values of the URL object; one or more can be specified
          schema:
            type: object
            required:
              - url
            properties:
              url:
                type: string
                format: url
                example: 'https://my.original.long.url/that/i-want/to/shorten'
                description: the original URL
              meta:
                type: object
                example: {
                  'a': 'foo',
                  'b': 'bar'
                }
              allow_reuse:
                type: boolean
                description: >
                  If a shortcut for the given URL already exists, then don't create a new one,
                  but return the existing short URL.
        responses:
          200:
            description: URL object patched successfully
            schema:
              $ref: '#/components/schemas/URL'
          404:
            description: 'shortcut to modify not found'
          405:
            description: 'method not allowed: `shortcut` not specified'
        """
        if not shortcut:
            raise MethodNotAllowed
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if not url:
            raise NotFound({'message': 'Shortcut does not exist', 'args': ['shortcut']})
        populate_from_dict(url, kwargs, ('url', 'allow_reuse', 'meta'))
        db.session.commit()
        current_app.logger.info('URL updated by %s: %s (%r)', g.token.name, url.shortcut, kwargs)
        return url

    @authorize_request_for_url
    @use_kwargs(URLSchemaManual)
    def delete(self, shortcut=None, **kwargs):
        """Delete an existing URL object.
        ---
        tags:
        - admins
        - users
        summary: deletes an existing URL object
        operationId: deleteURL
        description: >
          Delete an existing URL object
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: path
          name: shortcut
          description: the shortcut of the URL object to delete
          required: true
          type: string
        responses:
          204:
            description: token deleted successfully
          404:
            description: token to delete not found
          405:
            description: 'method not allowed: `shortcut` not specified'
        """
        if not shortcut:
            raise MethodNotAllowed
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if not url:
            raise NotFound({'message': 'Shortcut does not exist', 'args': ['shortcut']})
        db.session.delete(url)
        db.session.commit()
        current_app.logger.info('URL deleted by %s: %s -> <%s>', g.token.name, url.shortcut, url.url)
        return Response(status=204)

    @marshal_many_or_one(URLSchemaManual, 'shortcut', code=200)
    @use_kwargs(URLSchemaManual)
    @authorize_request_for_url
    def get(self, shortcut=None, **kwargs):
        """Obtain one or more URL objects.
        ---
        tags:
        - admins
        - users
        summary: returns one or more URL objects
        operationId: getURL
        description: >
          Obtain the URLs that match the given parameters. If `shortcut` is provided,
          then exactly one URL will be returned. Otherwise, a collection of tokens that
          match the provided parameters will be returned (maybe empty).
          Non-admin users may only obtain their own URLs (created with their API key).
        produces:
        - application/json
        parameters:
        - in: header
          name: Authorization
          description: the API key bearer
          type: string
          format: uuid
          required: true
        - in: path
          name: shortcut
          description: the shortcut of the URL to obtain - may be omitted
          required: true
          type: string
        - in: body
          name: filters
          description: the URL filters to apply
          schema:
            type: object
            properties:
              all:
                type: boolean
                description: whether to obtain all URLs; rest of filters ignored
              url:
                type: string
                format: url
                example: 'https://cern.ch'
                description: filter by URL
              meta:
                type: object
                description: filter by arbitrary metadata (key-value dictionary)
                example: {
                  'a': 'foo',
                  'b': 'bar'
                }
        responses:
          200:
            description: return a collection of the found URLs
            schema:
              format: array
              items:
                $ref: '#/components/schemas/URL'
          404:
            description: 'no URL found for the specified `shortcut`'
        """
        if not shortcut:
            meta = kwargs.get('meta')
            filters = []
            if kwargs.get('url'):
                filters.append(URL.url == kwargs.get('url'))
            if not g.token.is_admin or not kwargs.get('all'):
                filters.append(URL.token == g.token)
            if meta:
                filters.append(URL.meta.contains(meta))
            return URL.query.filter(*filters).all()
        url = URL.query.filter_by(shortcut=shortcut).one_or_none()
        if not url:
            raise NotFound({'message': 'Shortcut does not exist', 'args': ['shortcut']})
        return url


def populate_from_dict(obj, values, fields):
    for field in fields:
        if field in values:
            setattr(obj, field, values[field])


def create_new_url(data, shortcut=None):
    meta = data.get('meta') or{}
    if shortcut in current_app.config['BLACKLISTED_URLS']:
        raise generate_bad_request('invalid-shortcut', 'Invalid shortcut', args=['shortcut'])
    new_url = URL(token=g.token, meta=meta, shortcut=shortcut, is_custom=shortcut is not None)
    populate_from_dict(new_url, data, ('url', 'allow_reuse'))
    return new_url


def generate_bad_request(error_code, message, **kwargs):
    message_dict = {'code': error_code,
                    'description': message}
    message_dict.update(kwargs)
    return BadRequest(message_dict)

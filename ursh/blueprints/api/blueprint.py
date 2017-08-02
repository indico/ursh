from datetime import datetime, timezone

from flask import Blueprint, g, request
from sqlalchemy.exc import DataError, SQLAlchemyError
from werkzeug.exceptions import BadRequest, Conflict, MethodNotAllowed, NotFound

from ursh import db
from ursh.blueprints.api.handlers import (create_error_json, handle_bad_requests, handle_conflict, handle_db_errors,
                                          handle_internal_exceptions, handle_method_not_allowed, handle_not_found)
from ursh.blueprints.api.resources import TokenResource, URLResource
from ursh.models import Token


bp = Blueprint('urls', __name__)

tokens_view = TokenResource.as_view('tokens')
bp.add_url_rule('/tokens/', view_func=tokens_view)
bp.add_url_rule('/tokens/<api_key>', view_func=tokens_view)

urls_view = URLResource.as_view('urls')
bp.add_url_rule('/urls/', view_func=urls_view)
bp.add_url_rule('/urls/<shortcut>', view_func=urls_view)


@bp.before_request
def authorize_request():
    auth_token = get_token()
    error_json = create_error_json(401, 'invalid-token', 'The token you have entered is invalid')
    if not auth_token:
        return error_json
    try:
        token = Token.query.filter_by(api_key=auth_token).one_or_none()
    except DataError:
        return error_json
    if token is None or token.is_blocked:
        return error_json
    token.token_uses = Token.token_uses + 1
    token.last_access = datetime.now(timezone.utc)
    db.session.commit()

    g.token = token


def get_token():
    try:
        auth_type, auth_info = request.headers['Authorization'].split(None, 1)
        auth_type = auth_type.lower()
    except KeyError:
        return None
    return auth_info if auth_type == 'bearer' else None


bp.register_error_handler(BadRequest, handle_bad_requests)
bp.register_error_handler(SQLAlchemyError, handle_db_errors)
bp.register_error_handler(Conflict, handle_conflict)
bp.register_error_handler(NotFound, handle_not_found)
bp.register_error_handler(MethodNotAllowed, handle_method_not_allowed)
bp.register_error_handler(Exception, handle_internal_exceptions)

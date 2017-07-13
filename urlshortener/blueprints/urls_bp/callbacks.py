from datetime import datetime, timezone

from flask import Response, request
from werkzeug.exceptions import BadRequest

from urlshortener import db
from urlshortener.blueprints import urls_bp
from urlshortener.models import Token


@urls_bp.bp.before_request
def authorize_request():
    auth_token = request.headers.get('auth_token')
    if not auth_token:
        return BadRequest
    token = Token.query.filter_by(api_key=auth_token).one_or_none()
    if token is None or token.is_blocked:
        return Response(status=401)
    token.token_uses = Token.token_uses + 1
    token.last_access = datetime.now(timezone.utc)
    db.session.commit()

    request.token = token

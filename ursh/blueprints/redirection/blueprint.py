from flask import Blueprint, redirect, Response
from ursh.models import URL

bp = Blueprint('redirection', __name__)


@bp.route('/<shortcut>')
def redirect_to_url(shortcut):
    url = URL.query.filter_by(shortcut=shortcut).one_or_none()
    if not url:
        return Response(status=404)
    return redirect(url.url)

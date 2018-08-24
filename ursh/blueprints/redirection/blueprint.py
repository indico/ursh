from flask import Blueprint, Response, redirect

from ursh.models import URL


bp = Blueprint('redirection', __name__)


@bp.route('/<shortcut>')
def redirect_to_url(shortcut):
    """Redirect to the URL registered for the given shortcut.
    ---
    get:
      tags:
      - public
      summary: redirects to the URL registered for the given shortcut
      parameters:
      - in: path
        name: shortcut
        description: a previously generated or manually created shortcut
        type: string
      responses:
        302:
          description: redirect to the registered URL
        404:
          description: specified shortcut not found
    options:
      tags:
      - public
      summary: responds with the allowed HTTP methods
      parameters:
      - in: path
        name: shortcut
        description: a previously generated or manually created shortcut
        type: string
      responses:
        200:
          description: OK
    """
    url = URL.query.filter_by(shortcut=shortcut).one_or_none()
    if not url:
        return Response(status=404)
    return redirect(url.url)

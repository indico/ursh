from flask import Blueprint, Response, current_app, redirect


bp = Blueprint('misc', __name__)


@bp.route('/')
def index():
    """Index URL (no shortcut specified).
    ---
    get:
      tags:
      - public
      summary: shows a message or redirects to a configured url
      responses:
        200:
          description: default message if no redirect target is configured
        302:
          description: redirect to the configured target url
    options:
      tags:
      - public
      summary: responds with the allowed HTTP methods
      responses:
        200:
          description: OK
    """
    if current_app.config['INDEX_REDIRECT']:
        return redirect(current_app.config['INDEX_REDIRECT'])
    return Response('Nothing to see here', content_type='text/plain')

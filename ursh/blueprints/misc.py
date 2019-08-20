from flask import Blueprint, Response, current_app, redirect


bp = Blueprint('misc', __name__)


@bp.route('/')
def index():
    if current_app.config['INDEX_REDIRECT']:
        return redirect(current_app.config['INDEX_REDIRECT'])
    return Response('Nothing to see here', content_type='text/plain')

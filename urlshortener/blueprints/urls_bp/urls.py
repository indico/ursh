from urlshortener.blueprints import urls_bp
from urlshortener.blueprints.urls_bp.resources import TokenResource, URLResource


tokens_view = TokenResource.as_view('tokens')
urls_bp.bp.add_url_rule('/tokens/', defaults={'api_key': None}, view_func=tokens_view)
urls_bp.bp.add_url_rule('/tokens/<api_key>', view_func=tokens_view)

urls_view = URLResource.as_view('urls')
urls_bp.bp.add_url_rule('/urls/', defaults={'shortcut': None}, view_func=urls_view)
urls_bp.bp.add_url_rule('/urls/<shortcut>', view_func=urls_view)

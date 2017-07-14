from flask import jsonify

from urlshortener.blueprints.urls.errors import create_error_json


def handle_bad_requests(error):
    return jsonify({'status': error.code, 'error': error.description}), error.code


def handle_db_errors(error):
    return create_error_json(400, 'invalid-input', 'Your input is invalid')


def handle_url_exists(error):
    return create_error_json(409, 'url-exists', 'Shortcut already exists')


def handle_internal_exceptions(error):
    return create_error_json(500, 'internal-error', 'Sorry, something went wrong')

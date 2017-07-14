from flask import jsonify


API_ERRORS = [
    'missing-args',
    'insufficient-permissions',
    'invalid-token',
    'invalid-input',
    'internal-exception'
    'no-such-url',
]


class ShortcutAlreadyExistsError(Exception):
    pass


def create_error_json(status_code, error_code, message, **kwargs):
    message_dict = {
        'status': status_code,
        'error': {
            'code': error_code,
            'description': message
        }
    }
    message_dict['error'].update(kwargs)
    return jsonify(message_dict), status_code

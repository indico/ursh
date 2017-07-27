from flask import jsonify


def handle_bad_requests(error):
    return jsonify({'status': error.code, 'error': error.description}), error.code


def handle_db_errors(error):
    return create_error_json(400, 'invalid-input', 'Your input is invalid')


def handle_not_found(error):
    return create_error_json(404, 'not-found', error.description.get('message'), args=error.description.get('args'))


def handle_method_not_allowed(error):
    return create_error_json(405, 'invalid-method', 'This HTTP method is not allowed')


def handle_conflict(error):
    return create_error_json(409, 'conflict', error.description.get('message'), args=error.description.get('args'))


def handle_internal_exceptions(error):
    return create_error_json(500, 'internal-error', 'Sorry, something went wrong')


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

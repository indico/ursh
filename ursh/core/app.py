import datetime
import logging
import logging.config
import os

import yaml
from flask import Flask, request
from flask_apispec import FlaskApiSpec
from werkzeug.contrib.fixers import ProxyFix

from ursh import db
from ursh.core.cli import createdb_command
from ursh.util.db import import_all_models
from ursh.util.nested_query_parser import NestedQueryParser


CONFIG_OPTIONS = {
    'SQLALCHEMY_DATABASE_URI': 'str',
    'USE_PROXY': 'bool',
    'SECRET_KEY': 'str',
    'URL_LENGTH': 'int',
    'URL_PREFIX': 'str',
    'ENABLED_BLUEPRINTS': 'list',
    'BLACKLISTED_URLS': 'set'
}


def create_app(config_file=None, testing=False):
    """Factory to create the Flask application

    :param config_file: A python file from which to load the config.
                        If omitted, the config file must be set using
                        the ``URLSHORTENER_CONFIG`` environment variable.
                        If set, the environment variable is ignored
    :return: A `Flask` application instance
    """
    app = Flask('ursh')
    app.testing = testing
    _setup_logger(app)
    _load_config(app, config_file)
    _setup_db(app)
    _setup_cli(app)
    _register_handlers(app)
    _register_blueprints(app)
    _register_docs(app)
    return app


def _setup_logger(app):
    # Create our own logger since Flask's DebugLogger is a pain
    app._logger = logging.getLogger(app.logger.name)
    try:
        path = os.environ['URSH_LOGGING_CONFIG']
    except KeyError:
        path = os.path.join(app.root_path, 'logging.yml')
    with open(path) as f:
        logging.config.dictConfig(yaml.load(f))


def _load_config(app, config_file):
    app.config.from_pyfile('defaults.cfg')
    if config_file:
        app.config.from_pyfile(config_file)
    elif os.environ.get('URSH_CONFIG'):
        app.config.from_envvar('URSH_CONFIG')
    else:
        for key, type_ in CONFIG_OPTIONS.items():
            prefixed_key = 'URSH_' + key
            if prefixed_key in os.environ:
                value = os.environ.get(prefixed_key)
                if type_ == 'int':
                    value = int(value)
                elif type_ == 'list':
                    value = [x.strip() for x in value.split(',') if x.strip()]
                elif type_ == 'bool':
                    value = value.lower() in ('1', 'true')
                app.config[key] = value
    if app.config['USE_PROXY']:
        app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config['APISPEC_WEBARGS_PARSER'] = NestedQueryParser()


def _setup_db(app):
    # these settings should not be configurable in the config file so we
    # set them after loading the config file
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = False
    # ensure all models are imported even if not referenced from already-imported modules
    import_all_models(app.import_name)
    db.init_app(app)


def _setup_cli(app):
    app.cli.command('createdb', short_help='Creates the initial database structure.')(createdb_command)


def _register_handlers(app):
    @app.shell_context_processor
    def _extend_shell_context():
        ctx = {'db': db}
        ctx.update((name, cls) for name, cls in db.Model._decl_class_registry.items() if hasattr(cls, '__table__'))
        ctx.update((x, getattr(datetime, x)) for x in ('date', 'time', 'datetime', 'timedelta'))
        return ctx


def _register_blueprints(app):
    import ursh.blueprints
    blueprint_names = app.config['ENABLED_BLUEPRINTS']
    for name in blueprint_names:
        blueprint = getattr(ursh.blueprints, name)
        app.register_blueprint(blueprint)


def _register_docs(app):
    docs = FlaskApiSpec(app)
    docs.register_existing_resources()

from flask import current_app
from flask import json as _json

from ursh.cli.core import cli_group
from ursh.core.app import _register_openapi


@cli_group()
def cli():
    pass


@cli.command()
def export_json():
    """Export API spec to JSON"""
    if not current_app.config['ENABLE_SWAGGER']:
        _register_openapi(current_app)
    spec = current_app.config['APISPEC_SPEC']
    print(_json.dumps(spec.to_dict()))

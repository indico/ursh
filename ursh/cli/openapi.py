from flask import current_app
from flask import json as _json

from ursh.cli.core import cli_group


@cli_group()
def cli():
    pass


@cli.command()
def export_json():
    """Export API spec to JSON"""
    spec = current_app.config['APISPEC_SPEC']
    print(_json.dumps(spec.to_dict()))

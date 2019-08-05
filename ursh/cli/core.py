import click
from flask.cli import AppGroup, FlaskGroup

from ursh.cli.util import LazyGroup


_cli = AppGroup()
cli_command = _cli.command
cli_group = _cli.group
del _cli


def _get_ursh_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    import ursh
    message = 'ursh v{}'.format(ursh.__version__)
    click.echo(message, ctx.color)
    ctx.exit()


def _create_app(info):
    from ursh.core.app import create_app
    return create_app()


@click.group(cls=FlaskGroup, create_app=_create_app)
def cli():
    """ursh command line interface."""


@cli.group(cls=LazyGroup, import_name='ursh.cli.database:cli')
def db():
    """Perform database operations."""


@cli.group(cls=LazyGroup, import_name='ursh.cli.key:cli')
def apikey():
    """Perform API key related operations."""


@cli.group(cls=LazyGroup, import_name='ursh.cli.openapi:cli')
def openapi():
    """Perform OpenAPI related operations."""

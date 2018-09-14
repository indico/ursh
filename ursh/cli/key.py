import sys

import click
from sqlalchemy.exc import IntegrityError

from ursh import db
from ursh.cli.core import cli_group
from ursh.models import Token


def _print_usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))
        click.echo()


def _success(msg):
    click.echo('\n[SUCCESS] {}'.format(msg))
    sys.exit(0)


def _failure(msg):
    click.echo('\n[FAILURE] {}'.format(msg))
    sys.exit(1)


def _print_api_key(token):
    role = 'admin' if token.is_admin else 'user'
    click.echo('Role: {role}'.format(role=role))
    click.echo('Name: {name}'.format(name=token.name))
    click.echo('API key: {key}'.format(key=token.api_key))
    click.echo('Blocked: {blocked}'.format(blocked=token.is_blocked))


def _create_api_key(role, name, blocked):
    token = Token(name=name, is_admin=True if role == 'admin' else False, is_blocked=blocked)
    try:
        db.session.add(token)
        db.session.commit()
    except IntegrityError:
        _failure('An API key with the same name ("{name}") already exists.'.format(name=name))
    _print_api_key(token)
    if blocked:
        _success('The above listed API key is blocked - you will not be able to use it until it is unblocked.')
    else:
        _success('You can now use the API key listed above to make ursh requests.')


def _toggle_api_key_block(blocked, **kwargs):
    filters = {k: v for k, v in kwargs.items() if v}
    token = Token.query.filter_by(**filters).one_or_none()
    if not token:
        _failure('No API key was found for the specified filters.')
        return
    if token.is_blocked != blocked:
        token.is_blocked = blocked
        db.session.commit()
    _success('API key {} successfully.'.format('unblocked' if not blocked else 'blocked'))


def _validate_filters_or_die(filters, command):
    if not any(filters.values()):
        _print_usage(command)
        _failure('{method}: please specify at least one option.'.format(method=command.name))


@cli_group()
def cli():
    pass


@cli.command()
@click.argument('role', type=click.Choice(['admin', 'user']))
@click.argument('token_name')
@click.argument('blocked', type=bool, default=False)
def create(role, token_name, blocked):
    """Create a new API token."""
    _create_api_key(role, token_name, blocked)


@cli.command()
@click.option('--name', '-n', metavar='NAME')
@click.option('--api-key', '-k', metavar='API_KEY')
def delete(**kwargs):
    """Delete an API key."""
    _validate_filters_or_die(kwargs, delete)
    filters = {k: v for k, v in kwargs.items() if v}
    token = Token.query.filter_by(**filters).one_or_none()
    if token:
        try:
            db.session.delete(token)
            db.session.commit()
        except IntegrityError:
            _failure('Could not delete the specified API key as there are URLs associated with it.')
    else:
        _failure('No API key was found for the specified filters.')


@cli.command()
@click.option('--name', '-n', metavar='NAME')
@click.option('--api-key', '-k', metavar='API_KEY')
def get(**kwargs):
    """Obtain an API key."""
    _validate_filters_or_die(kwargs, get)
    filters = {k: v for k, v in kwargs.items() if v}
    token = Token.query.filter_by(**filters).one_or_none()
    if token:
        _print_api_key(token)
    else:
        _failure('No API key was found for the specified filters.')


@cli.command()
@click.option('--name', '-n', metavar='NAME')
@click.option('--api-key', '-k', metavar='API_KEY')
def block(**kwargs):
    """Block an API key."""
    _validate_filters_or_die(kwargs, block)
    _toggle_api_key_block(True, **kwargs)


@cli.command()
@click.option('--name', '-n', metavar='NAME')
@click.option('--api-key', '-k', metavar='API_KEY')
def unblock(**kwargs):
    """Unblock an API key."""
    _validate_filters_or_die(kwargs, unblock)
    _toggle_api_key_block(False, **kwargs)

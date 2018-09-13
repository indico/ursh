from ursh import db
from ursh.cli.core import cli_group


@cli_group()
def cli():
    pass


@cli.command()
def create():
    """Creates the initial database structure"""
    db.create_all()

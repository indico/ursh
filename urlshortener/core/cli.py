from flask.cli import with_appcontext

from urlshortener import db


@with_appcontext
def createdb_command():
    """Creates the initial database structure.
    This command provides a quick way to setup the initial database.
    It only creates new objects; existing ones are left untouched.
    Because of this the command is best used against an empty database
    to ensure the database and the models are completely in sync.
    """
    # TODO: replace with something nicer that provides access to alembic
    # for upgrades/downgrades once we get close to a production setup
    db.create_all()

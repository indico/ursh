import os
import re
import shutil
import signal
import subprocess
import tempfile

import pytest

from ursh.core.app import create_app
from ursh.core.db import db as db_

POSTGRES_MIN_VERSION = (9, 6)
POSTGRES_VERSION = (12,)
POSTGRES_PREFIX = '/usr/lib/postgresql/{version}/bin'.format(version='.'.join(map(str, POSTGRES_VERSION)))


@pytest.fixture(scope='session')
def app():
    """Create the flask app"""
    return create_app(testing=True)


@pytest.fixture(autouse=True)
def app_context(app):
    """Create a flask app context"""
    with app.app_context():
        yield app


@pytest.fixture
def request_context(app_context):
    """Create a flask request context"""
    with app_context.test_request_context():
        yield


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(scope='session')
def postgresql():
    """
    Provide a clean temporary PostgreSQL server/database.
    If the environment variable `URSH_TEST_DATABASE_URI` is set, this fixture
    will do nothing and simply return the connection string from that variable
    """
    # Use existing database
    if 'URSH_TEST_DATABASE_URI' in os.environ:
        yield os.environ['URSH_TEST_DATABASE_URI']
        return

    db_name = 'test'

    initdb_command = 'initdb'
    pg_ctl_command = 'pg_ctl'
    if not shutil.which('initdb'):
        initdb_command = os.path.join(POSTGRES_PREFIX, initdb_command)
    if not shutil.which('pg_ctl'):
        pg_ctl_command = os.path.join(POSTGRES_PREFIX, pg_ctl_command)

    # Ensure we have initdb and a recent enough postgres version
    try:
        version_output = subprocess.check_output([initdb_command, '--version']).decode('utf-8')
        pg_version = tuple(map(int, re.match(r'.*\(PostgreSQL\) ((?:\d+\.?)+).*', version_output).group(1).split('.')))
        if pg_version < POSTGRES_MIN_VERSION:
            pytest.skip(f'PostgreSQL version is too old: {version_output}')
    except Exception as e:
        pytest.skip(f'Could not retrieve PostgreSQL version: {e}')

    # Prepare server instance and a test database
    temp_dir = tempfile.mkdtemp(prefix='indicotestpg.')
    postgres_args = f'-h "" -k "{temp_dir}"'
    try:
        subprocess.check_call([initdb_command, '--encoding', 'utf8', temp_dir])
        subprocess.check_call([pg_ctl_command, '-D', temp_dir, '-w', '-o', postgres_args, 'start'])
        subprocess.check_call(['createdb', '-h', temp_dir, db_name])
    except Exception as e:
        shutil.rmtree(temp_dir)
        pytest.skip(f'could not init/start postgresql: {e}')

    yield f'postgresql:///{db_name}?host={temp_dir}'

    try:
        subprocess.check_call([pg_ctl_command, '-D', temp_dir, '-m', 'immediate', 'stop'])
    except Exception as e:
        # If it failed for any reason, try killing it
        try:
            with open(os.path.join(temp_dir, 'postmaster.pid')) as f:
                pid = int(f.readline().strip())
                os.kill(pid, signal.SIGKILL)
            pytest.skip(f'Could not stop postgresql; killed it instead: {e}')
        except Exception as e:
            pytest.skip(f'Could not stop/kill postgresql: {e}')
    finally:
        shutil.rmtree(temp_dir)


@pytest.fixture(scope='session')
def database(app, postgresql):
    """
    Create a test database which is destroyed afterwards
    Used only internally, if you need to access the database use `db` instead to ensure
    your modifications are not persistent!
    """
    app.config['SQLALCHEMY_DATABASE_URI'] = postgresql
    app.extensions.pop('sqlalchemy', None)
    db_.init_app(app)
    if 'URSH_TEST_DATABASE_URI' in os.environ and os.environ.get('URSH_TEST_DATABASE_HAS_TABLES') == '1':
        yield db_
        return
    with app.app_context():
        db_.create_all()
    yield db_
    with app.app_context():
        db_.session.remove()
        db_.drop_all()


@pytest.fixture
def db(database, monkeypatch):
    """Provide database access and ensures changes do not persist"""
    # Prevent database/session modifications
    monkeypatch.setattr(database.session, 'commit', database.session.flush)
    monkeypatch.setattr(database.session, 'remove', lambda: None)
    yield database
    database.session.rollback()
    database.session.remove()

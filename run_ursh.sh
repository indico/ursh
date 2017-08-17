#!/bin/bash
source /venv/bin/activate
export SQLALCHEMY_DATABASE_URI="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
export FLASK_APP=ursh._cliapp
until psql -lqt "$PGDATABASE" | cut -d '|' -f 1 | grep -qw "$PGDATABASE"; do
    sleep 1
done
echo 'Preparing DB...'
flask createdb
uwsgi --ini ursh.ini

#!/bin/bash
source /venv/bin/activate
export SQLALCHEMY_DATABASE_URI="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
export FLASK_APP=ursh._cliapp
until [ $'psql -lqt "$PGDATABASE" | cut -d \| -f 1 | grep -qw "$PGDATABASE"' -eq 0 ]; do
    sleep 1
done
if [ $? -eq 1 ]; then
    echo 'Preparing DB...'
    flask createdb
fi
uwsgi --ini ursh.ini

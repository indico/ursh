#!/bin/bash
source /venv/bin/activate
export SQLALCHEMY_DATABASE_URI="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
export FLASK_APP=ursh._cliapp
psql -lqt $PGDATABASE | cut -d \| -f 1 | grep -qw $PGDATABASE
until [ $? -eq 0 ]; do
    sleep 1
    psql -lqt $PGDATABASE | cut -d \| -f 1 | grep -qw $PGDATABASE
done
if [ $? -eq 1 ]; then
    echo 'Preparing DB...'
    flask createdb
fi
uwsgi --ini ursh.ini

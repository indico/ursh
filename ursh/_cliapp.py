# XXX: Never import this package. It only exists so the `flask`
# command can use it (using `FLASK_APP=ursh._cliapp`) as it cannot
# use an app factory directly

from ursh.core.app import create_app


app = create_app()

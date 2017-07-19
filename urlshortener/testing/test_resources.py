import pytest


@pytest.mark.usefixtures('app', 'db')
def test_create_token(app, db):
    assert False
    a = []
    print(a[9])
    raise Exception
    print(dir(app))
    pytest.set_trace()
    return False

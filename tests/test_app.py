# tests/test_app.py
import pytest

from webapp.app import create_app

@pytest.fixture
def app():
    app = create_app()
    return app

def test_import_app(app):
    # just ensure factory works
    assert app.config["ENV"] in ("test", "production")

def test_home_endpoint(app):
    client = app.test_client()
    rv = client.get("/")  # adjust to your actual home route
    assert rv.status_code in (200, 302)  # login redirect or home page

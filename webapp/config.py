# webapp/config.py

import os
from dotenv import load_dotenv

# Load any .env file in the project root
load_dotenv()

class BaseConfig:
    """Common settings."""
    SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-me-in-env")
    LETSENCRYPT_DOMAIN = os.getenv("LETSENCRYPT_DOMAIN", "")

class ProdConfig(BaseConfig):
    """Production (Postgres) settings."""
    ENV = "production"
    DEBUG = False

    DB_HOST = os.getenv("PROD_DB_HOST")
    DB_PORT = os.getenv("PROD_DB_PORT")
    DB_USER = os.getenv("PROD_DB_USER")
    DB_PASSWORD = os.getenv("PROD_DB_PASSWORD")
    DB_NAME = os.getenv("PROD_DB_NAME")

    # Flask-Login
    LOGIN_VIEW = "auth.login"

class TestConfig(BaseConfig):
    """Test (SQLite) settings."""
    ENV = "test"
    DEBUG = True

    # The sqlite file sits next to this config module
    TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test.db")
    LOGIN_VIEW = "auth.login"

    # Credentials for seeding the test admin
    TEST_ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin")
    TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "adminpass")

# dash/config.py
from dotenv import load_dotenv
import os

# Load your .env so os.getenv() actually reads TEST_ADMIN_PASSWORD, etc.
load_dotenv()

class BaseConfig:
    SECRET_KEY = os.getenv("APP_SECRET_KEY")
    LOGIN_VIEW = "auth.login"

class ProdConfig(BaseConfig):
    DEBUG = False
    ENV = "production"
    DB_HOST     = os.getenv("DB_HOST_PROD", "")
    DB_PORT     = int(os.getenv("DB_PORT_PROD", "5432"))
    DB_USER     = os.getenv("DB_USER_PROD", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD_PROD", "")
    DB_NAME     = os.getenv("DB_NAME_PROD", "")

class TestConfig(BaseConfig):
    DEBUG = True
    ENV = "test"
    DB_HOST     = os.getenv("DB_HOST_TEST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT_TEST", "5432"))
    DB_USER     = os.getenv("DB_USER_TEST", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD_TEST", "")
    DB_NAME     = os.getenv("DB_NAME_TEST", "")

    # **No hardcoded fallback**—must come from your .env
    TEST_ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME")
    TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD")

    # fail fast if you forgot to set them
    if not TEST_ADMIN_USERNAME or not TEST_ADMIN_PASSWORD:
        raise RuntimeError(
            "Both TEST_ADMIN_USERNAME and TEST_ADMIN_PASSWORD must be set in .env when ENV=test"
        )

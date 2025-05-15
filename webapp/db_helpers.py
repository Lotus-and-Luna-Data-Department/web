# dash/db_helpers.py
import os
import psycopg2

def get_db_connection():
    env = os.getenv("ENV", "production").lower()
    if env == "test":
        sslmode = "disable"
        host, port, user, password, dbname = (
            os.getenv("DB_HOST_TEST"),
            os.getenv("DB_PORT_TEST"),
            os.getenv("DB_USER_TEST"),
            os.getenv("DB_PASSWORD_TEST"),
            os.getenv("DB_NAME_TEST"),
        )
    else:
        sslmode = "require"
        host, port, user, password, dbname = (
            os.getenv("DB_HOST_PROD"),
            os.getenv("DB_PORT_PROD"),
            os.getenv("DB_USER_PROD"),
            os.getenv("DB_PASSWORD_PROD"),
            os.getenv("DB_NAME_PROD"),
        )

    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        sslmode=sslmode
    )

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-apenas-para-desenvolvimento")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "database": os.getenv("DB_NAME", "coffeetime"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@coffeetime.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123")

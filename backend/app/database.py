from pathlib import Path

import click
import mysql.connector
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(**current_app.config["DB_CONFIG"])
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection and connection.is_connected():
        connection.close()


def fetch_all(query, params=()):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_one(query, params=()):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    return row


def execute(query, params=(), commit=True):
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute(query, params)
    last_id = cursor.lastrowid
    if commit:
        connection.commit()
    cursor.close()
    return last_id


@click.command("init-db")
def init_database_command():
    config = current_app.config["DB_CONFIG"].copy()
    database_name = config.pop("database")
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{database_name}`")
    schema = Path(current_app.root_path).parents[1] / "database" / "schema.sql"
    for statement in schema.read_text(encoding="utf-8").split(";"):
        if statement.strip():
            cursor.execute(statement)
            if statement.lstrip().upper().startswith("CREATE TABLE IF NOT EXISTS COUPONS"):
                cursor.execute("SHOW COLUMNS FROM coupons LIKE 'first_order_only'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE coupons ADD COLUMN first_order_only BOOLEAN NOT NULL DEFAULT FALSE AFTER expires_at")
    cursor.execute("SHOW COLUMNS FROM coupons LIKE 'once_per_user'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE coupons ADD COLUMN once_per_user BOOLEAN NOT NULL DEFAULT FALSE AFTER first_order_only")
    cursor.execute("SHOW COLUMNS FROM orders LIKE 'coupon_code'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(40) NULL")
    cursor.execute("SHOW COLUMNS FROM orders LIKE 'discount'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE orders ADD COLUMN discount DECIMAL(10,2) NOT NULL DEFAULT 0")
    cursor.execute("SHOW COLUMNS FROM products LIKE 'image_data'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE products ADD COLUMN image_data LONGBLOB NULL AFTER price")
    cursor.execute("SHOW COLUMNS FROM products LIKE 'image_mime'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE products ADD COLUMN image_mime VARCHAR(50) NULL AFTER image_data")

    for legacy_column in ("image_url", "image_source_url"):
        cursor.execute(f"SHOW COLUMNS FROM products LIKE '{legacy_column}'")
        if cursor.fetchone():
            cursor.execute(f"ALTER TABLE products DROP COLUMN `{legacy_column}`")
    cursor.execute(
        "INSERT IGNORE INTO users (name, email, password_hash, phone, role) VALUES (%s, %s, %s, %s, 'admin')",
        ("Administrador", current_app.config["ADMIN_EMAIL"], generate_password_hash(current_app.config["ADMIN_PASSWORD"]), "11999999999"),
    )
    connection.commit()
    cursor.close()
    connection.close()
    click.echo("Banco criado e dados iniciais inseridos.")

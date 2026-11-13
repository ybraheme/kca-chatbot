"""Ensure the database and bootstrap admin exist on every run.
Called by Home.py and both pages. Idempotent — safe to run repeatedly.
"""
import os
import bcrypt
import config
from chatbot.database import init_schema, transaction


def ensure_db():
    """Create tables and seed the admin if they don't exist yet."""
    # 1. Ensure the data directory exists (needed on Streamlit Cloud)
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)

    # 2. Ensure the schema exists (idempotent — CREATE TABLE IF NOT EXISTS)
    init_schema()

    # 3. Ensure the bootstrap admin exists
    with transaction() as conn:
        row = conn.execute(
            "SELECT admin_id FROM ADMIN_ACCOUNT WHERE username = ?",
            (config.ADMIN_USERNAME,),
        ).fetchone()
        if not row:
            pw_hash = bcrypt.hashpw(
                config.ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            )
            conn.execute(
                "INSERT INTO ADMIN_ACCOUNT (username, password_hash, role) "
                "VALUES (?, ?, 'admin')",
                (config.ADMIN_USERNAME, pw_hash.decode("utf-8")),
            )
"""Create tables and seed admin account. Run once."""
import bcrypt
import config
from chatbot.database import init_schema, transaction


def seed_admin():
    """Insert the bootstrap admin with a bcrypt hash (SEC-1)."""
    pw_hash = bcrypt.hashpw(config.ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt())
    with transaction() as conn:
        row = conn.execute(
            "SELECT admin_id FROM ADMIN_ACCOUNT WHERE username = ?",
            (config.ADMIN_USERNAME,),
        ).fetchone()
        if row:
            print(f"[init_db] Admin '{config.ADMIN_USERNAME}' already exists — skipping.")
        else:
            conn.execute(
                "INSERT INTO ADMIN_ACCOUNT (username, password_hash, role) VALUES (?, ?, 'admin')",
                (config.ADMIN_USERNAME, pw_hash.decode("utf-8")),
            )
            print(f"[init_db] Created admin '{config.ADMIN_USERNAME}'.")


if __name__ == "__main__":
    init_schema()
    seed_admin()
    print(f"[init_db] Schema ready at {config.DB_PATH}")
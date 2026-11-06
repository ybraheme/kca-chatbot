"""SQLite connection and schema. Uses parameterised queries only (SI-3, SEC-5)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS KNOWLEDGE_DOCUMENT (
    document_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title              TEXT    NOT NULL,
    category           TEXT    NOT NULL,
    responsible_office TEXT    NOT NULL,
    source_reference   TEXT,
    review_date        DATE    NOT NULL,
    review_interval_days INTEGER DEFAULT 180,
    status             TEXT    NOT NULL DEFAULT 'active'
                       CHECK (status IN ('active','retired')),
    content            TEXT,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS PASSAGE (
    passage_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id    INTEGER NOT NULL REFERENCES KNOWLEDGE_DOCUMENT(document_id) ON DELETE CASCADE,
    passage_text   TEXT    NOT NULL,
    passage_index  INTEGER NOT NULL,
    token_count    INTEGER DEFAULT 0,
    embedding      BLOB
);

CREATE TABLE IF NOT EXISTS QUERY_LOG (
    log_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    question_anonymised  TEXT     NOT NULL,
    matched_document_id  INTEGER REFERENCES KNOWLEDGE_DOCUMENT(document_id),
    matched_document_ids TEXT,
    outcome              TEXT     NOT NULL CHECK (outcome IN ('answered','declined','error','cached')),
    response_time_ms     INTEGER  NOT NULL,
    topic_category       TEXT,
    declined_reason      TEXT,
    redaction_flags      INTEGER  DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ADMIN_ACCOUNT (
    admin_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    role            TEXT    DEFAULT 'admin',
    last_login_at   DATETIME,
    failed_attempts INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS KB_CHANGE_RECORD (
    change_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER REFERENCES KNOWLEDGE_DOCUMENT(document_id),
    admin_id        INTEGER REFERENCES ADMIN_ACCOUNT(admin_id),
    action          TEXT    NOT NULL CHECK (action IN ('add','edit','retire')),
    changed_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    change_summary  TEXT
);

CREATE INDEX IF NOT EXISTS idx_ql_timestamp   ON QUERY_LOG(timestamp);
CREATE INDEX IF NOT EXISTS idx_pass_doc       ON PASSAGE(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_status     ON KNOWLEDGE_DOCUMENT(status);
"""


def get_connection(db_path=None):
    """Open a connection with foreign keys on and a row factory."""
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(db_path=None):
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def transaction(db_path=None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
"""Anonymised query logging (FR-18, FR-19, FR-20, FR-21, FR-23)."""
from datetime import datetime, timedelta
import config
from chatbot.anonymiser import anonymise
from chatbot.database import get_connection


def log_query(record: dict, db_path=None) -> int:
    """Insert a query log row. Returns log_id."""
    masked, flags = anonymise(record["question"])
    docs = record.get("matched_document_ids") or []
    docs_str = ",".join(str(d) for d in docs) if docs else None
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO QUERY_LOG
               (question_anonymised, matched_document_id, matched_document_ids,
                outcome, response_time_ms, topic_category, declined_reason, redaction_flags)
               VALUES (?,?,?,?,?,?,?,?)""",
            (masked,
             record.get("top_document_id"),
             docs_str,
             record["outcome"],
             record["response_time_ms"],
             record.get("topic_category"),
             record.get("declined_reason"),
             flags),
        )
        conn.commit()
        return cur.lastrowid


def prune_old(db_path=None) -> int:
    """Delete entries older than LOG_RETENTION_DAYS (FR-21). Returns row count deleted."""
    cutoff = (datetime.utcnow() - timedelta(days=config.LOG_RETENTION_DAYS)).isoformat(sep=" ")
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM QUERY_LOG WHERE timestamp < ?", (cutoff,))
        conn.commit()
        return cur.rowcount
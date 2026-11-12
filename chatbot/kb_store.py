"""Knowledge-base CRUD + ingestion (FR-25 to FR-32, SDS Fig 10)."""
from datetime import datetime, date
from pathlib import Path
from chatbot.database import get_connection, transaction

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SUPPORTED = {".txt", ".pdf", ".docx"}


def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    if ext == ".docx":
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"Unsupported format: {ext}")


def _split(text: str) -> list[str]:
    """Split ~500 chars with 50-char overlap."""
    text = " ".join(text.split())
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + CHUNK_SIZE])
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks or [text[:CHUNK_SIZE]]


def add_document(*, title, category, responsible_office, source_reference,
                 review_date, content, admin_id, db_path=None) -> int:
    """Add a doc, split into passages, write KB_CHANGE_RECORD. Returns document_id."""
    if not title or not category or not responsible_office or not review_date or not content:
        raise ValueError("Missing required field")
    
    passages = _split(content)
    with transaction(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO KNOWLEDGE_DOCUMENT
               (title, category, responsible_office, source_reference, review_date, status, content)
               VALUES (?,?,?,?,?, 'active', ?)""",
            (title, category, responsible_office, source_reference, review_date, content),
        )
        doc_id = cur.lastrowid
        for idx, p in enumerate(passages):
            conn.execute(
                "INSERT INTO PASSAGE (document_id, passage_text, passage_index) VALUES (?,?,?)",
                (doc_id, p, idx),
            )
        conn.execute(
            """INSERT INTO KB_CHANGE_RECORD (document_id, admin_id, action, change_summary)
               VALUES (?,?, 'add', ?)""",
            (doc_id, admin_id, f"Added: {title}"),
        )
        return doc_id


def add_from_file(file_path, *, title, category, responsible_office,
                  source_reference, review_date, admin_id, db_path=None) -> int:
    p = Path(file_path)
    if p.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported format: {p.suffix}")
    content = _extract_text(p)
    if not content.strip():
        raise ValueError("Empty file")
    return add_document(title=title, category=category,
                        responsible_office=responsible_office,
                        source_reference=source_reference, review_date=review_date,
                        content=content, admin_id=admin_id, db_path=db_path)


def edit_document(doc_id, *, admin_id, db_path=None, **fields) -> None:
    allowed = {"title", "category", "responsible_office", "source_reference",
               "review_date", "content"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    with transaction(db_path) as conn:
        set_sql = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE KNOWLEDGE_DOCUMENT SET {set_sql}, updated_at = CURRENT_TIMESTAMP "
            f"WHERE document_id = ?",
            (*updates.values(), doc_id),
        )
        if "content" in updates:
            conn.execute("DELETE FROM PASSAGE WHERE document_id = ?", (doc_id,))
            for idx, p in enumerate(_split(updates["content"])):
                conn.execute(
                    "INSERT INTO PASSAGE (document_id, passage_text, passage_index) VALUES (?,?,?)",
                    (doc_id, p, idx),
                )
        conn.execute(
            "INSERT INTO KB_CHANGE_RECORD (document_id, admin_id, action, change_summary) "
            "VALUES (?,?, 'edit', ?)",
            (doc_id, admin_id, f"Edited: {', '.join(updates.keys())}"),
        )


def retire_document(doc_id, *, admin_id, db_path=None) -> None:
    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE KNOWLEDGE_DOCUMENT SET status = 'retired', updated_at = CURRENT_TIMESTAMP "
            "WHERE document_id = ?",
            (doc_id,),
        )
        conn.execute(
            "INSERT INTO KB_CHANGE_RECORD (document_id, admin_id, action, change_summary) "
            "VALUES (?,?, 'retire', 'Retired')",
            (doc_id, admin_id),
        )


def list_documents(db_path=None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT document_id, title, category, responsible_office, source_reference,
                      review_date, status
               FROM KNOWLEDGE_DOCUMENT ORDER BY document_id"""
        ).fetchall()
        return [dict(r) for r in rows]


def is_outdated(review_date_str: str, interval_days: int) -> bool:
    """True if today > review_date + interval_days (FR-16)."""
    try:
        rd = datetime.strptime(str(review_date_str)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    return (date.today() - rd).days > interval_days
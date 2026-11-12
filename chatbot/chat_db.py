"""Persistent chat history (DB storage)."""
import uuid
from chatbot.database import get_connection

def create_session(first_question: str) -> str:
    session_id = str(uuid.uuid4())
    title = first_question[:40] + "..." if len(first_question) > 40 else first_question
    with get_connection() as conn:
        conn.execute("INSERT INTO CHAT_SESSION (session_id, title) VALUES (?, ?)", (session_id, title))
        conn.commit()
    return session_id

def get_sessions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT session_id, title, created_at FROM CHAT_SESSION ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def delete_session(session_id: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM CHAT_SESSION WHERE session_id = ?", (session_id,))
        conn.commit()

def get_messages(session_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT role, content, source_title, review_date, model_used FROM CHAT_MESSAGE WHERE session_id = ? ORDER BY created_at ASC", (session_id,)).fetchall()
        return [dict(r) for r in rows]

def save_message(session_id: str, role: str, content: str, source_title=None, review_date=None, model_used=None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO CHAT_MESSAGE (session_id, role, content, source_title, review_date, model_used) VALUES (?,?,?,?,?,?)",
            (session_id, role, content, source_title, review_date, model_used)
        )
        conn.commit()
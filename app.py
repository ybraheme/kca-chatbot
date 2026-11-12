"""Orchestrator: social + emergency + RAG + meta + cache + rate limit."""
import time
import config
from chatbot.retriever import retrieve
from chatbot.prompt_builder import build
from chatbot.llm_client import generate, LLMUnavailable
from chatbot.cache import get_cache
from chatbot.logger import log_query
from chatbot.database import get_connection
from chatbot.social import classify_social, SOCIAL_RESPONSES, is_meta_question, is_emergency
from chatbot.rate_limiter import RateLimiter


def _get_limiter():
    import streamlit as st
    if "rate_limiter" not in st.session_state:
        st.session_state.rate_limiter = RateLimiter()
    return st.session_state.rate_limiter


def get_active_categories() -> list:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT category, COUNT(*) as n FROM KNOWLEDGE_DOCUMENT
            WHERE status = 'active' GROUP BY category ORDER BY n DESC
        """).fetchall()
        return [r["category"] for r in rows]


def get_active_topics_summary(max_items: int = 3) -> str:
    cats = get_active_categories()
    if not cats:
        return "general KCA information"
    if len(cats) <= max_items:
        if len(cats) == 1: return cats[0]
        return ", ".join(cats[:-1]) + f", and {cats[-1]}"
    return ", ".join(cats[:max_items])


def _handle_meta_question(question, history):
    last_answer = history[-1]["a"]
    prompt = (
        f"You are a friendly KCA student support assistant. "
        f"A student did not understand this previous answer:\n\n\"{last_answer}\"\n\n"
        f"The student now asks: \"{question}\"\n\n"
        f"Re-explain the answer in simpler, clearer language. "
        f"Do not invent new information. Keep any existing source citation."
    )
    try:
        result = generate(prompt)
        return {"answer": result["text"], "sources": [], "outcome": "answered",
                "model_used": result["model_used"]}
    except LLMUnavailable:
        return {"answer": "Please try again in a moment.", "sources": [],
                "outcome": "error", "model_used": ""}


def _handle_emergency(question):
    prompt = (
        f"You are the KCA Student Support Assistant. A student sent this urgent message:\n\n"
        f"\"{question}\"\n\n"
        f"Respond with warmth. Acknowledge their concern. State clearly you cannot "
        f"resolve this yourself and they need a human. Direct them to the right office "
        f"(Finance Room 12, +254 700 000 000; Registrar; or Exams Office). "
        f"Do not invent deadlines or processes. Keep it under 100 words. "
        f"Be kind. Use 2-3 natural sentences, no bullet lists."
    )
    try:
        result = generate(prompt)
        return {"answer": result["text"], "sources": [], "outcome": "answered",
                "model_used": f"emergency/{result['model_used']}"}
    except LLMUnavailable:
        return {"answer": "Please contact the Finance Office immediately: Room 12, +254 700 000 000.",
                "sources": [], "outcome": "answered", "model_used": "local/emergency"}


def handle_request(question: str, history: list = None) -> dict:
    if history is None:
        history = []
    start = time.time()

    # 1. Validate
    if not question or not question.strip():
        return {"answer": "Please type a question.", "sources": [], "outcome": "declined", "model_used": ""}
    if len(question) > config.MAX_QUESTION_LEN:
        return {"answer": f"Too long (max {config.MAX_QUESTION_LEN} chars).", "sources": [], "outcome": "declined", "model_used": ""}

    # 2. Social fast-path (0 credits)
    social = classify_social(question)
    if social == "capability":
        cats = get_active_categories()
        if cats:
            msg = f"I currently have documents covering: **{', '.join(cats)}**. What would you like to know?"
        else:
            msg = "My knowledge base is empty right now. Please contact the Admissions Office."
        return {"answer": msg, "sources": [], "outcome": "answered", "model_used": "local/template"}
    if social:
        return {"answer": SOCIAL_RESPONSES[social], "sources": [], "outcome": "answered", "model_used": "local/template"}

    # 3. Meta (explain simpler) — 1 credit
    if is_meta_question(question) and history:
        return _handle_meta_question(question, history)

    # 4. Rate limit (SEC-6)
    limiter = _get_limiter()
    allowed, msg = limiter.allow()
    if not allowed:
        return {"answer": msg, "sources": [], "outcome": "declined", "model_used": ""}

    # 5. Cache (FR-44)
    cache = get_cache()
    cached = cache.get(question)
    if cached:
        elapsed_ms = int((time.time() - start) * 1000)
        log_query({"question": question, "outcome": "cached", "response_time_ms": elapsed_ms,
                   "matched_document_ids": cached.get("matched_document_ids"),
                   "top_document_id": cached.get("top_document_id"),
                   "topic_category": cached.get("topic_category")})
        return {**cached, "outcome": "cached"}

    # 6. Emergency (Option C) — 1 credit
    if is_emergency(question):
        result = _handle_emergency(question)
        log_query({"question": question, "outcome": "answered",
                   "response_time_ms": int((time.time() - start) * 1000),
                   "declined_reason": "emergency_handled"})
        return result

    # 7. RAG (Option A) — 1 credit
    passages = retrieve(question)
    if not passages:
        top = get_active_topics_summary(max_items=3)
        answer = (
            f"I'm not sure about that in my current documents. "
            f"I cover things like **{top}** — is there something there I can help with? "
            f"For general KCA information, check kcau.ac.ke or contact the Admissions Office."
        )
        elapsed_ms = int((time.time() - start) * 1000)
        log_query({"question": question, "outcome": "declined", "response_time_ms": elapsed_ms,
                   "declined_reason": "no_relevant_passage"})
        return {"answer": answer, "sources": [], "outcome": "declined", "model_used": "local/fallback"}

    prompt = build(question, passages, history)
    try:
        result = generate(prompt)
        answer = result["text"]
        model_used = result["model_used"]
    except LLMUnavailable:
        elapsed_ms = int((time.time() - start) * 1000)
        log_query({"question": question, "outcome": "error", "response_time_ms": elapsed_ms,
                   "matched_document_ids": [p["document_id"] for p in passages],
                   "top_document_id": passages[0]["document_id"]})
        return {"answer": "The assistant is temporarily unavailable. Please try again later.",
                "sources": [], "outcome": "error", "model_used": ""}

    if "NOT_IN_SOURCES" in answer:
        top = get_active_topics_summary(max_items=3)
        answer = (
            f"I couldn't find a clear answer to that. My documents cover **{top}** — "
            f"please contact the responsible office for this one."
        )
        elapsed_ms = int((time.time() - start) * 1000)
        log_query({"question": question, "outcome": "declined", "response_time_ms": elapsed_ms,
                   "matched_document_ids": [p["document_id"] for p in passages],
                   "top_document_id": passages[0]["document_id"],
                   "declined_reason": "llm_not_in_sources"})
        return {"answer": answer, "sources": [], "outcome": "declined", "model_used": model_used}

    elapsed_ms = int((time.time() - start) * 1000)
    doc_ids = [p["document_id"] for p in passages]
    topic = passages[0].get("category", "Unclassified")
    response = {
        "answer": answer, "sources": passages, "outcome": "answered",
        "model_used": model_used,
        "matched_document_ids": doc_ids,
        "top_document_id": passages[0]["document_id"],
        "topic_category": topic,
    }
    cache.set(question, response)
    log_query({"question": question, "outcome": "answered", "response_time_ms": elapsed_ms,
               "matched_document_ids": doc_ids, "top_document_id": passages[0]["document_id"],
               "topic_category": topic})
    return response
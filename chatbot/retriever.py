"""TF-IDF retriever (FR-09, FR-13, FR-14, SDS §3.0)."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import config
from chatbot.database import get_connection


SMS_REPLACEMENTS = {
    " u ": " you ", " r ": " are ", " pls ": " please ", " plz ": " please ",
    " thx ": " thanks ", " wat ": " what ", " dnt ": " do not ",
    " cant ": " cannot ", " im ": " i am ", " ive ": " i have ",
    " xam ": " exam ", " xams ": " exams ", " skul ": " school ",
    " fee ": " fee ", " reg ": " registration ", " reg ": " registration ",
}


def _normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for s, l in SMS_REPLACEMENTS.items():
        text = f" {text} ".replace(s, l).strip()
    words = text.split()
    stemmed = []
    for word in words:
        for suffix in ("ations", "ation", "ments", "ment", "ings", "ing",
                       "ions", "ion", "es", "s"):
            if len(word) > len(suffix) + 2 and word.endswith(suffix):
                word = word[:-len(suffix)]
                break
        stemmed.append(word)
    return " ".join(stemmed)


def load_index(db_path=None):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT p.passage_id, p.document_id, p.passage_text,
                      d.title, d.category, d.responsible_office, d.review_date
               FROM PASSAGE p
               JOIN KNOWLEDGE_DOCUMENT d ON d.document_id = p.document_id
               WHERE d.status = 'active'"""
        ).fetchall()

    passages = [dict(r) for r in rows]
    if not passages:
        return [], None, None
    normalised = [_normalise(p["passage_text"]) for p in passages]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vec.fit_transform(normalised)
    return passages, vec, matrix


def retrieve(question: str, *, threshold=None, top_k=None, db_path=None) -> list:
    threshold = config.RELEVANCE_THRESHOLD if threshold is None else threshold
    top_k = config.TOP_K if top_k is None else top_k

    passages, vec, matrix = load_index(db_path)
    if not passages:
        return []

    q_norm = _normalise(question)
    q_vec = vec.transform([q_norm])
    sims = cosine_similarity(q_vec, matrix).flatten()

    ranked = sorted(
        [(i, float(s)) for i, s in enumerate(sims) if s >= threshold],
        key=lambda x: x[1], reverse=True,
    )[:top_k]

    out = []
    for i, score in ranked:
        p = dict(passages[i])
        p["score"] = round(score, 4)
        out.append(p)
    return out
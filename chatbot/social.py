"""Social / small-talk classification with fuzzy matching for broken English."""

def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, remove common SMS shorthand."""
    import re
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)  # strip punctuation
    text = re.sub(r"\s+", " ", text).strip()
    # Common SMS/typo substitutions
    replacements = {
        " u ": " you ", " r ": " are ", " pls ": " please ", " plz ": " please ",
        " thx ": " thanks ", " thanx ": " thanks ", " 2 ": " to ", " 4 ": " for ",
        " msg ": " message ", " xam ": " exam ", " xams ": " exams ",
        " fee ": " fee ", " fees ": " fees ", " skul ": " school ",
        " wat ": " what ", " wats ": " what is ", " watsup ": " what is up ",
        " hv ": " have ", " dnt ": " do not ", " dont ": " do not ",
        " cant ": " cannot ", " won t ": " will not ", " im ": " i am ",
        " ive ": " i have ", " id ": " i would ", " il ": " i will ",
    }
    for short, long in replacements.items():
        text = f" {text} ".replace(short, long).strip()
    return text


# Detectors use normalized form + fuzzy keyword matching
GREETING = ["hello", "hi", "hey", "hallo", "hiya", "greetings",
            "good morning", "good afternoon", "good evening",
            "how are you", "how you doing", "how is it going",
            "what is up", "morning", "afternoon", "evening"]

THANKS = ["thank you", "thanks", "thankyou", "thx", "appreciate", "asante", "asante sana"]

GOODBYE = ["bye", "goodbye", "see you", "later", "good night", "cheers", "exit", "quit"]

IDENTITY = ["who are you", "what are you", "what is your name", "your name",
            "are you a bot", "are you a robot", "are you human", "what do you do",
            "how do you work", "you are a bot", "you are robot"]

CAPABILITY = ["what can you do", "what can i ask", "what do you cover",
              "what topics", "what categories", "what subjects",
              "name all", "list all", "what are you capable of",
              "what do you help with", "what can you help with",
              "what can you help me with"]


def classify_social(question: str):
    q = _normalise(question)
    # Social messages are short
    if len(q.split()) > 10:
        return None
    # Check identity first (most specific)
    for p in IDENTITY:
        if p in q:
            return "identity"
    for p in CAPABILITY:
        if p in q:
            return "capability"
    # Greetings: allow the whole message to be a greeting, even with typos
    for p in GREETING:
        if q == p or q.startswith(p + " ") or q.endswith(" " + p):
            return "greeting"
    for p in THANKS:
        if p in q:
            return "thanks"
    for p in GOODBYE:
        if q == p or q.startswith(p + " "):
            return "goodbye"
    return None


SOCIAL_RESPONSES = {
    "greeting": (
        "Hello! 👋 I'm the KCA Student Support Assistant. I can help you with questions "
        "about fees, exams, registration, and campus offices. What would you like to know?"
    ),
    "thanks": "You're welcome! 😊 Is there anything else I can help you with?",
    "goodbye": "Goodbye! Good luck with your studies. 📚",
    "identity": (
        "I'm the KCA Student Support Assistant — an automated chatbot that answers "
        "questions about KCA University using official documents. I'm not a human, "
        "but I'm available 24/7. What can I look up for you?"
    ),
}


def is_meta_question(question: str) -> bool:
    q = _normalise(question)
    triggers = ["explain simpler", "simpler", "do not understand", "not understand",
                "what does that mean", "rephrase", "in simple terms", "eli5",
                "can you clarify", "what do you mean", "explain that again",
                "say that again", "more detail", "tell me more", "i do not get it",
                "i do not understand", "explain again"]
    return any(t in q for t in triggers)


def is_emergency(question: str) -> bool:
    q = _normalise(question)
    triggers = [
        "going to fail", "im going to fail", "i will fail", "will fail",
        "expelled", "suspended", "missed the deadline", "missed deadline",
        "exam is tomorrow", "exam tomorrow", "cannot afford", "cannot pay",
        "do not know what to do", "do not know what do",
        "please help", "urgent", "emergency", "desperate",
        "financial ruin", "panicking", "panicking about", "i am panicking",
        "suicidal", "want to die", "ending it", "depressed","missed my exam", "missed exam", "missed exams", "missed the exam",
"failed my exam", "failed exam", "i failed",
    ]
    return any(t in q for t in triggers)
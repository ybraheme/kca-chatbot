from chatbot.retriever import load_index, _stem
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3

# Check what's actually in the DB
c = sqlite3.connect('data/chatbot.db')
print("=== Documents in DB ===")
for row in c.execute("SELECT document_id, title, status FROM KNOWLEDGE_DOCUMENT"):
    print(f"  Doc {row[0]}: {row[1]} (status={row[2]})")

print("\n=== Passages in DB ===")
for row in c.execute("SELECT passage_id, document_id, substr(passage_text, 1, 80) FROM PASSAGE LIMIT 5"):
    print(f"  Passage {row[0]} (doc {row[1]}): {row[2]}...")
c.close()

# Now debug the retrieval
print("\n=== Retrieval debug ===")
question = "When must I pay my fees?"
q_stemmed = _stem(question)
print(f"Question: {question}")
print(f"Stemmed:  {q_stemmed}")

passages, vec, matrix = load_index()
print(f"Active passages loaded: {len(passages)}")

if passages:
    print(f"\nStemmed passage 1: {_stem(passages[0]['passage_text'])[:100]}...")
    q_vec = vec.transform([q_stemmed])
    sims = cosine_similarity(q_vec, matrix).flatten()
    print(f"\nTop 3 scores: {sorted(sims, reverse=True)[:3]}")
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from chatbot.kb_store import add_document
from chatbot.retriever import retrieve

# 1. Get the admin ID to attribute the upload
c = sqlite3.connect('data/chatbot.db')
admin_id = c.execute('SELECT admin_id FROM ADMIN_ACCOUNT').fetchone()[0]
c.close()

# 2. Add a test document
text = (
    "The deadline for fee payment in Trimester 1 is 15th September 2026. "
    "Students must clear all balances before sitting for their exams. "
    "Payments can be made via the KCA student portal using M-Pesa or Bank Transfer."
)
doc_id = add_document(
    title='Fee Structure 2026', 
    category='Fees', 
    responsible_office='Finance Office',
    source_reference='KCA-FEE-2026', 
    review_date='2026-09-01', 
    content=text,
    admin_id=admin_id
)
print('Document added with ID:', doc_id)

# 3. Test the retriever
print('\n--- Searching for: "When must I pay my fees?" ---')
results = retrieve('When must I pay my fees?', threshold=0.01)

if not results:
    print('FAILED: No passages found.')
else:
    for r in results:
        print(f"[Score: {r['score']}] {r['title']} -> {r['passage_text'][:80]}...")
    print('\nSUCCESS! The RAG engine is working.')
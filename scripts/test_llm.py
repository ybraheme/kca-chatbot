import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chatbot.retriever import retrieve
from chatbot.prompt_builder import build
from chatbot.llm_client import generate

question = "When must I pay my fees?"
print(f"Question: {question}\n")

# 1. Retrieve
passages = retrieve(question)
print(f"Retrieved {len(passages)} passages\n")

# 2. Build prompt
prompt = build(question, passages, [])
print(f"Prompt length: {len(prompt)} chars\n")

# 3. Call LLM
print("Calling LLM...")
try:
    result = generate(prompt)
    print(f"\nModel used: {result['model_used']}")
    print(f"Answer:\n{result['text']}")
except Exception as e:
    print(f"\nFAILED: {e}")
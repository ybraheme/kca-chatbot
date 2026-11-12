import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import csv
import time
from app import handle_request

TEST_SET_FILE = "test_data/test_set_100.csv"
RESULTS_FILE = "test_data/test_results.csv"

def run_tests():
    print("Starting 100-question test set...")
    results = []
    
    try:
        with open(TEST_SET_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            questions = list(reader)
    except FileNotFoundError:
        print(f"ERROR: {TEST_SET_FILE} not found. Please create it.")
        return

    print(f"Loaded {len(questions)} questions.\n")

    answered_under_10s = 0
    answered = 0
    declined = 0
    errors = 0

    for i, q in enumerate(questions, 1):
        question = q["question"]
        print(f"[{i}/{len(questions)}] {question}")
        
        start = time.time()
        res = handle_request(question)
        elapsed = time.time() - start
        
        outcome = res["outcome"]
        if outcome == "answered" or outcome == "cached":
            answered += 1
            if elapsed < 10.0:
                answered_under_10s += 1
        elif outcome == "declined":
            declined += 1
        else:
            errors += 1
            
        results.append({
            "question": question,
            "answer": res["answer"],
            "outcome": outcome,
            "time_s": round(elapsed, 2),
            "model": res["model_used"]
        })
        
        print(f"   -> {outcome.upper()} in {elapsed:.2f}s")

    # Save results
    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "answer", "outcome", "time_s", "model"])
        writer.writeheader()
        writer.writerows(results)

    # Summary
    total = len(questions)
    print("\n=== TEST SUMMARY ===")
    print(f"Total questions:       {total}")
    print(f"Answered:              {answered}")
    print(f"Declined:              {declined}")
    print(f"Errors:                {errors}")
    
    if total > 0:
        pct_speed = (answered_under_10s / total) * 100
        print(f"\nAC-1 (<10s):           {answered_under_10s}/{total} ({pct_speed:.1f}%) - {'PASS' if pct_speed >= 95 else 'FAIL'}")
    
    print(f"Results saved to:      {RESULTS_FILE}")
    print("You can now review the answers in the CSV to score accuracy (AC-2).")

if __name__ == "__main__":
    run_tests()
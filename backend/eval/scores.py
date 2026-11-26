"""Show the best semantic score for every eval question, to choose MIN_SCORE for the abstention threshold.

Usage (from backend/):  python -m eval.scores --file eval/questions.json
"""
import argparse
import json

from app.services.retrieval_service import retrieve


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="eval/questions.json")
    args = ap.parse_args()
    answer, refuse = [], []
    for q in json.load(open(args.file, encoding="utf-8-sig")):
        _, best = retrieve(q["question"], q.get("workspace_id", "default"), 5, "semantic")
        (refuse if q.get("should_abstain") else answer).append(best)
        print(f"{best:6.3f}  {'SHOULD REFUSE' if q.get('should_abstain') else 'answerable   '}  {q['question'][:70]}")
    print()
    if answer and refuse:
        lo, hi = min(answer), max(refuse)
        print(f"lowest answerable score : {lo:.3f}")
        print(f"highest refusal score   : {hi:.3f}")
        if lo > hi:
            print(f"-> a good MIN_SCORE is about {(lo + hi) / 2:.2f}")
        else:
            print("-> the ranges overlap; pick a value just under the lowest answerable score and let the model refuse the rest")


if __name__ == "__main__":
    main()

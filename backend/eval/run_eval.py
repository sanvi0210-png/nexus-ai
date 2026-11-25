"""Compare retrieval modes on your own question set.

Usage (from backend/):  python -m eval.run_eval --file eval/questions.json --k 5
"""
import argparse
import json
import time

from app.config import settings
from app.services.retrieval_service import MODES, retrieve


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="eval/questions.json")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()
    questions = json.load(open(args.file, encoding="utf-8-sig"))

    answerable = [q for q in questions if not q.get("should_abstain")]
    unanswerable = [q for q in questions if q.get("should_abstain")]
    print(f"{len(answerable)} answerable, {len(unanswerable)} should-abstain questions, k={args.k}\n")
    print(f"{'mode':<15}{'hit@k':>8}{'abstain ok':>12}{'avg ms':>10}")

    for mode in MODES:
        retrieve("warm up", questions[0].get("workspace_id", "default"), args.k, mode)  # load models first
        hits_ok, abstain_ok, times = 0, 0, []
        for q in questions:
            ws = q.get("workspace_id", "default")
            t = time.perf_counter()
            hits, best = retrieve(q["question"], ws, args.k, mode)
            times.append((time.perf_counter() - t) * 1000)
            if q.get("should_abstain"):
                abstain_ok += best < settings.min_score
            else:
                page = q.get("expected_page")
                hits_ok += any(
                    h["filename"] == q["expected_file"] and (page is None or h["page"] == page) for h in hits
                )
        hit = f"{hits_ok}/{len(answerable)}" if answerable else "-"
        ab = f"{abstain_ok}/{len(unanswerable)}" if unanswerable else "-"
        print(f"{mode:<15}{hit:>8}{ab:>12}{sum(times) / len(times):>10.0f}")


if __name__ == "__main__":
    main()

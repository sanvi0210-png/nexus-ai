def reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Merge ranked lists by rank (not raw score). Earlier lists win ties for the stored item."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            key = item["id"]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            items.setdefault(key, item)
    return [items[key] for key in sorted(scores, key=scores.get, reverse=True)]

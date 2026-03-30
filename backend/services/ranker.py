from typing import List, Dict


def rank_candidates(scored_candidates: List[Dict]) -> List[Dict]:
    """
    Sort by final_score descending and assign rank.
    Returns ranked list with rank field added.
    """
    sorted_candidates = sorted(
        scored_candidates, key=lambda x: x["final_score"], reverse=True
    )
    for i, candidate in enumerate(sorted_candidates):
        candidate["rank"] = i + 1
    return sorted_candidates


def get_top_n(ranked_candidates: List[Dict], n: int) -> List[Dict]:
    """Filter to top N candidates."""
    if n <= 0:
        return ranked_candidates
    return ranked_candidates[:n]

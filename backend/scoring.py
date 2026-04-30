from collections.abc import Iterable

DEFAULT_KEYWORD_WEIGHTS = {
    "hot oil circulation": 60,
    "hot oiling": 60,
    "hoc": 50,
    "chemical injection": 50,
    "chemical dosing": 45,
    "corrosion inhibitor": 40,
    "scale inhibitor": 40,
    "wax removal": 40,
    "paraffin": 40,
    "flow assurance": 35,
    "dosing pump": 25,
    "charter hire of rig": 65,
    "coil tubing unit": 65,
    "nitrogen unit": 65,
    "pumper": 65,
    "acid pumper": 65,
    "cementing unit": 65,
    "charter hire 30 ton rig": 65,
    "charter hire 50 ton rig": 65,
    "o&m rig": 65,
    "mehsana": 25,
    "cambay": 25,
    "ahmedabad": 20,
    "gujarat": 20,
    "ongc": 25,
    "oil india": 25,
    "gail": 20,
    "civil work": -40,
    "housekeeping": -40,
    "furniture": -30,
    "painting": -25,
    "canteen": -40,
    "security service": -40,
}


def score_tender(text: str, keyword_weights: dict[str, float] | None = None) -> tuple[list[str], float, str, str]:
    weights = keyword_weights or DEFAULT_KEYWORD_WEIGHTS
    normalized_text = text.lower()
    matched = []
    raw_score = 0.0

    for keyword, weight in weights.items():
        if keyword.lower() in normalized_text:
            matched.append(keyword)
            raw_score += weight

    score = max(min(round(raw_score, 2), 100), 0)
    status = classify_status(score)
    recommendation = recommend_bid(status)
    return matched, score, status, recommendation


def classify_status(score: float) -> str:
    if score >= 80:
        return "High Priority"
    if score >= 50:
        return "Review"
    return "Low Priority"


def recommend_bid(status: str) -> str:
    if status == "High Priority":
        return "Bid"
    if status == "Review":
        return "Review"
    return "No Bid"


def weights_from_keywords(keywords: Iterable[object]) -> dict[str, float]:
    weights = {}
    for keyword in keywords:
        weights[keyword.term.lower()] = keyword.weight
    return weights or DEFAULT_KEYWORD_WEIGHTS

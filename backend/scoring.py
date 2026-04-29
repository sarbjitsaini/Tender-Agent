POSITIVE_WEIGHTS = {
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
    "mehsana": 25,
    "cambay": 25,
    "ahmedabad": 20,
    "gujarat": 20,
    "ongc": 25,
    "oil india": 25,
    "gail": 20,
}

NEGATIVE_WEIGHTS = {
    "civil work": -40,
    "housekeeping": -40,
    "furniture": -30,
    "painting": -25,
    "canteen": -40,
    "security service": -40,
}


def score_tender(company: str, title: str, location: str) -> tuple[list[str], float]:
    haystack = f"{company} {title} {location}".lower()
    matched = []
    score = 0.0

    for keyword, weight in POSITIVE_WEIGHTS.items():
        if keyword in haystack:
            matched.append(keyword)
            score += weight

    for keyword, weight in NEGATIVE_WEIGHTS.items():
        if keyword in haystack:
            matched.append(keyword)
            score += weight

    return matched, max(0.0, min(100.0, score))


def priority_from_score(score: float) -> tuple[str, str]:
    if score >= 80:
        return "High Priority", "Bid"
    if 50 <= score <= 79:
        return "Review", "Review"
    return "Low Priority", "No-bid"

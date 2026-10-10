def classify(z, pct, rule="stat"):
    if rule == "tracking":
        return "critical"
    if rule == "budget":
        return "high"
    a, p = abs(z), abs(pct)
    if a >= 7 or p >= 0.80:
        return "critical"
    if a >= 5.5 or p >= 0.50:
        return "high"
    if a >= 4.5 or p >= 0.35:
        return "medium"
    return "low"

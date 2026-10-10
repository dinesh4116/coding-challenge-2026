"""Per-campaign robust baseline (median + MAD), weekday-aware to absorb weekly seasonality."""
import numpy as np

WINDOW = 28        # days of history used
MIN_HISTORY = 14   # days required before alerting starts

def build(hist, metric, weekday):
    same = hist.loc[hist["weekday"] == weekday, metric].astype(float)
    base = same if len(same) >= 4 else hist[metric].astype(float)
    med = float(np.median(base))
    mad = float(np.median(np.abs(base - med)))
    # Floor the scale at 10% of the median so very stable series don't alert on tiny moves
    scale = max(1.4826 * mad, 0.10 * abs(med), np.sqrt(abs(med)), 1e-6)  # sqrt(med) = Poisson noise floor for counts
    return {"median": med, "scale": scale, "n": len(base)}

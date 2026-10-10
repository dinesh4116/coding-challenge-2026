import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

RNG = np.random.default_rng(42)
SIZE = 96  # analysis resolution

# ----------------------------------------------------------------------
# 1. FEATURE EXTRACTION
# ----------------------------------------------------------------------
HUE_NAMES = [(20, "red"), (45, "orange"), (70, "yellow"), (165, "green"),
             (200, "cyan"), (260, "blue"), (340, "purple/pink"), (361, "red")]


def hue_family(h_deg: float) -> str:
    for upper, name in HUE_NAMES:
        if h_deg < upper:
            return name
    return "red"


def bg_family(rgb) -> str:
    r, g, b = [x / 255 for x in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    s = 0 if mx == 0 else (mx - mn) / mx
    if s < 0.15:
        return "white/light" if mx > 0.75 else "black/dark" if mx < 0.3 else "grey"
    h = np.array([[[*[int(x * 255) for x in (r, g, b)]]]], dtype=np.uint8)
    hsv = np.array(Image.fromarray(h, "RGB").convert("HSV"))[0, 0].astype(float)
    return hue_family(hsv[0] * 360 / 255)


def extract_features(path_or_img) -> dict:
    img = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    w0, h0 = img.size
    rgb = img.convert("RGB").resize((SIZE, SIZE))
    a = np.asarray(rgb, dtype=np.float32)
    hsv = np.asarray(rgb.convert("HSV"), dtype=np.float32)
    H, S, V = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) / 255

    # colourfulness (Hasler & Susstrunk)
    rg = a[..., 0] - a[..., 1]
    yb = 0.5 * (a[..., 0] + a[..., 1]) - a[..., 2]
    colorful = (np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean())) / 255

    # edge density (Sobel on luminance)
    gx = (lum[:-2, 2:] + 2 * lum[1:-1, 2:] + lum[2:, 2:]) - (lum[:-2, :-2] + 2 * lum[1:-1, :-2] + lum[2:, :-2])
    gy = (lum[2:, :-2] + 2 * lum[2:, 1:-1] + lum[2:, 2:]) - (lum[:-2, :-2] + 2 * lum[:-2, 1:-1] + lum[:-2, 2:])
    edges = float((np.hypot(gx, gy) > 0.5).mean())

    # background = border pixels
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3),
                             a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    bg = border.mean(0)
    whitespace = float((np.linalg.norm(a - bg, axis=-1) < 30).mean())
    centre = lum[30:66, 30:66].mean()
    edge_l = lum[np.r_[0:6, SIZE - 6:SIZE]].mean()

    # dominant hue among saturated pixels
    mask = (S > 0.25) & (V > 0.2)
    if mask.mean() > 0.05:
        fams = pd.Series([hue_family(h) for h in H[mask]]).value_counts()
        dom = fams.index[0]
        warm = fams.reindex(["red", "orange", "yellow"]).fillna(0).sum() / fams.sum()
    else:
        dom, warm = "neutral (little colour)", 0.0

    ratio = w0 / h0
    return {
        "brightness": float(lum.mean()),
        "contrast": float(lum.std()),
        "saturation": float(S.mean()),
        "colorfulness": float(colorful),
        "edges": edges,
        "whitespace": whitespace,
        "centerContrast": float(abs(centre - edge_l)),
        "warmShare": float(warm),
        "bgBrightness": float(border.mean() / 255),
        "domHue": dom,
        "bgFamily": bg_family(bg),
        "orient": "landscape" if ratio > 1.15 else "portrait" if ratio < 0.87 else "square",
    }


# ----------------------------------------------------------------------
# 2. ATTRIBUTE TABLE
# ----------------------------------------------------------------------
CONT = {
    "brightness": "Brighter overall", "contrast": "Higher luminance contrast",
    "saturation": "More saturated", "colorfulness": "More colourful",
    "edges": "Busier / more cluttered (edge density)",
    "whitespace": "More empty background (minimalist)",
    "centerContrast": "Strong centre-vs-edge focal contrast",
    "warmShare": "Warmer palette (red/orange/yellow share)",
    "bgBrightness": "Lighter background",
}
CAT = {"domHue": "Dominant hue", "bgFamily": "Background colour", "orient": "Format"}


def build_attributes(df: pd.DataFrame) -> dict:
    attrs = {}
    for col, label in CONT.items():
        flag = (df[col] > df[col].median()).to_numpy()
        if 0 < flag.sum() < len(flag):
            attrs[f"{label} (above vs below median)"] = flag
    for col, label in CAT.items():
        for val in df[col].unique():
            attrs[f"{label}: {val}"] = (df[col] == val).to_numpy()
    return attrs


# ----------------------------------------------------------------------
# 3. HONEST STATISTICS
# ----------------------------------------------------------------------
def benjamini_hochberg(p):
    p = np.asarray(p)
    order = np.argsort(p)
    m = len(p)
    q = np.empty(m)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        prev = min(prev, p[i] * m / (rank + 1))
        q[i] = prev
    return q


def test_attribute(flag, num, den, perms, n_boot=1000):
    n = len(flag)
    A, B = np.where(flag)[0], np.where(~flag)[0]
    nA, nB = len(A), len(B)
    a1, a2, b1, b2 = num[A].sum(), den[A].sum(), num[B].sum(), den[B].sum()
    out = dict(nA=nA, nB=nB, evA=a1, evB=b1)
    if nA < 2 or nB < 2 or a2 == 0 or b2 == 0 or b1 == 0:
        out["testable"] = False
        return out
    rA, rB = a1 / a2, b1 / b2
    diff = rA - rB

    # permutation test on the pooled-rate difference (shuffle creative labels)
    pa = perms[:, :nA]
    pb = perms[:, nA:]
    ra = num[pa].sum(1) / np.maximum(den[pa].sum(1), 1e-12)
    rb = num[pb].sum(1) / np.maximum(den[pb].sum(1), 1e-12)
    p = (np.sum(np.abs(ra - rb) >= abs(diff) - 1e-15) + 1) / (len(perms) + 1)

    # bootstrap CI on relative lift (resample creatives within each group)
    ia = RNG.integers(0, nA, (n_boot, nA))
    ib = RNG.integers(0, nB, (n_boot, nB))
    xa = num[A][ia].sum(1) / np.maximum(den[A][ia].sum(1), 1e-12)
    xb = num[B][ib].sum(1) / np.maximum(den[B][ib].sum(1), 1e-12)
    ok = xb > 0
    lifts = xa[ok] / xb[ok] - 1
    lo, hi = np.percentile(lifts, [2.5, 97.5])
    out.update(testable=True, rA=rA, rB=rB, lift=rA / rB - 1, lo=lo, hi=hi, p=p)
    return out


def analyse(df, metric="ctr", min_creatives=20, min_events=30, n_perm=2000):
    if metric == "ctr":
        num, den, name = df.clicks.to_numpy(float), df.impressions.to_numpy(float), "CTR"
    elif metric == "cvr":
        num, den, name = df.conversions.to_numpy(float), df.clicks.to_numpy(float), "conversion rate"
    else:
        num, den, name = df.conversions.to_numpy(float), df.impressions.to_numpy(float), "conversions/impression"
    keep = den > 0
    df, num, den = df[keep].reset_index(drop=True), num[keep], den[keep]

    attrs = build_attributes(df)
    perms = RNG.random((n_perm, len(df))).argsort(axis=1)
    rows = []
    for k, (label, flag) in enumerate(attrs.items(), 1):
        r = test_attribute(flag, num, den, perms)
        r["attribute"] = label
        rows.append(r)
    print(f"  tested {len(attrs)} attributes", file=sys.stderr)
    res = pd.DataFrame(rows)

    t = res.testable == True  # noqa: E712
    res.loc[t, "q"] = benjamini_hochberg(res.loc[t, "p"].to_numpy())

    verdicts, whys = [], []
    for _, r in res.iterrows():
        if not r.testable:
            verdicts.append("UNDERPOWERED")
            whys.append("Untestable: a group has <2 creatives or no events.")
            continue
        small_n, small_e = min(r.nA, r.nB), min(r.evA, r.evB)
        if small_n < min_creatives or small_e < min_events:
            verdicts.append("UNDERPOWERED")
            whys.append(f"Smallest group has {small_n} creatives / {int(small_e)} events "
                        f"(need >= {min_creatives} / {min_events}). Lift is not reliable.")
        elif r.q < 0.10 and (r.lo > 0 or r.hi < 0):
            verdicts.append("SUPPORTED")
            whys.append("Survives FDR correction (q<0.10) and 95% CI excludes zero.")
        elif r.p < 0.05:
            verdicts.append("SUGGESTIVE")
            whys.append("Raw p<0.05 but fails multiple-testing correction. Treat as a hypothesis.")
        elif r.lo > -0.25 and r.hi < 0.25:
            verdicts.append("NO CLEAR EFFECT")
            whys.append("CI within about +/-25%.")
        else:
            verdicts.append("NO CLEAR EFFECT")
            whys.append("Inconclusive: CI too wide to rule out a sizeable effect.")
    res["verdict"], res["why"] = verdicts, whys
    order = {"SUPPORTED": 0, "SUGGESTIVE": 1, "NO CLEAR EFFECT": 2, "UNDERPOWERED": 3}
    res["_o"] = res.verdict.map(order)
    res = res.sort_values(["_o", "q"], na_position="last").drop(columns="_o").reset_index(drop=True)
    return res, name, len(df)


# ----------------------------------------------------------------------
# 4. REPORTING + CREATIVE BRIEF
# ----------------------------------------------------------------------
def pct(x, d=0):
    return f"{x * 100:+.{d}f}%"


def write_report(res, metric_name, n, df, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    res.drop(columns=["testable"], errors="ignore").to_csv(outdir / "findings.csv", index=False)

    counts = res.verdict.value_counts()
    tested = res[res.testable == True]  # noqa: E712
    half = ((tested.hi - tested.lo) / 2).median() if len(tested) else float("nan")

    L = [f"# Ad Creative Intelligence - {metric_name}\n",
         f"*Sample:* {n} creatives, {int(df.impressions.sum()):,} impressions, "
         f"{int(df.clicks.sum()):,} clicks. {len(res)} attributes tested.\n",
         "*Method:* effects are relative lift (with vs without attribute) in pooled rate. "
         "95% CI from creative-level bootstrap; p from permutation test; p-values corrected "
         "for multiple testing (Benjamini-Hochberg).\n",
         f"*Overall confidence:* a typical attribute's 95% CI is about +/-{half * 100:.0f}% on the lift, "
         "so only larger effects are detectable. Data are observational: findings are associations, "
         "not causes.\n",
         "| Verdict | Count |\n|---|---|"]
    for v in ["SUPPORTED", "SUGGESTIVE", "NO CLEAR EFFECT", "UNDERPOWERED"]:
        L.append(f"| {v} | {counts.get(v, 0)} |")

    for v, title in [("SUPPORTED", "Supported findings"),
                     ("SUGGESTIVE", "Suggestive (hypotheses, not conclusions)"),
                     ("UNDERPOWERED", "Reported as unsupported (too little data)"),
                     ("NO CLEAR EFFECT", "No clear effect / inconclusive")]:
        sub = res[res.verdict == v]
        L.append(f"\n## {title}\n")
        if sub.empty:
            L.append("None.")
            continue
        L.append("| Attribute | n with / without | Lift [95% CI] | p / q | Note |\n|---|---|---|---|---|")
        for _, r in sub.iterrows():
            if r.testable:
                L.append(f"| {r.attribute} | {r.nA} / {r.nB} | {pct(r.lift)} [{pct(r.lo)}, {pct(r.hi)}] "
                         f"| {r.p:.3f} / {r.q:.3f} | {r.why} |")
            else:
                L.append(f"| {r.attribute} | {r.nA} / {r.nB} | - | - | {r.why} |")

    L.append("\n## Creative brief for next batch\n")
    sup, sug = res[res.verdict == "SUPPORTED"], res[res.verdict == "SUGGESTIVE"]
    if sup.empty and sug.empty:
        L.append("No attribute meets the evidence bar yet. Do not change the brief on this data; "
                 "use the next batch to A/B test specific hypotheses.")
    for _, r in sup.iterrows():
        L.append(f"- *{'Lean into' if r.lift > 0 else 'Avoid'}:* {r.attribute} "
                 f"({metric_name} {pct(r.lift)}, CI {pct(r.lo)} to {pct(r.hi)}, n={r.nA} vs {r.nB}).")
    for _, r in sug.iterrows():
        L.append(f"- *Test next:* {r.attribute} ({pct(r.lift)}, p={r.p:.3f}, q={r.q:.2f}) - run as controlled A/B.")
    big = res[(res.verdict == "UNDERPOWERED") & (res.testable == True) & (res.lift.abs() > 0.3)].head(4)  # noqa: E712
    if len(big):
        L.append("\n*Do not over-read:* " + "; ".join(
            f"{r.attribute} ({pct(r.lift)}, n={min(r.nA, r.nB)} in smaller group)" for _, r in big.iterrows())
            + ". These rest on too few creatives; include more of each in the next batch.")

    (outdir / "report.md").write_text("\n".join(L), encoding="utf-8")
    return "\n".join(L)


# ----------------------------------------------------------------------
# 5. DATA LOADING / DEMO DATA
# ----------------------------------------------------------------------
def load_dataset(img_dir, metrics_csv):
    m = pd.read_csv(metrics_csv)
    m.columns = [c.strip().lower() for c in m.columns]
    idcol = next((c for c in m.columns if c in
                  ("id", "file", "filename", "file_name", "image", "image_name", "creative", "creative_id", "ad", "ad_id", "name")),
                 m.columns[0])
    ren = {}
    for c in m.columns:
        if c.startswith("impr"):
            ren[c] = "impressions"
        elif c.startswith("click"):
            ren[c] = "clicks"
        elif c.startswith("conv"):
            ren[c] = "conversions"
        elif c in ("spend", "cost"):
            ren[c] = "spend"
    m = m.rename(columns=ren)
    m["_key"] = m[idcol].astype(str).str.strip().str.replace(r"\.[A-Za-z0-9]+$", "", regex=True).str.lower()

    rows, skipped = [], 0
    files = [p for p in Path(img_dir).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp")]
    lookup = m.set_index("_key")
    for i, p in enumerate(sorted(files), 1):
        if i % 25 == 0 or i == len(files):
            print(f"  extracting features {i}/{len(files)}", file=sys.stderr)
        key = p.stem.lower()
        if key not in lookup.index:
            skipped += 1
            continue
        try:
            f = extract_features(p)
        except Exception:
            skipped += 1
            continue
        r = lookup.loc[key]
        rows.append({"id": p.name, **f, "spend": r.get("spend", 0), "impressions": r["impressions"],
                     "clicks": r["clicks"], "conversions": r["conversions"]})
    print(file=sys.stderr)
    if skipped:
        print(f"Skipped {skipped} image(s) with no matching CSV row or unreadable.")
    return pd.DataFrame(rows)


def make_demo(folder="demo_data", n=150):
    """Synthetic ads. Hidden truth: warm backgrounds +30% CTR, minimal layout +12%.
    5 'red background' ads get a lucky x2.9 CTR (pure noise) - the trap."""
    img_dir = Path(folder) / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    pal = {"red": (210, 40, 45), "orange": (235, 130, 40), "yellow": (240, 200, 50), "green": (60, 160, 90),
           "blue": (50, 100, 200), "purple": (140, 70, 170), "white": (245, 245, 240),
           "dark": (30, 32, 40), "grey": (130, 130, 135)}
    keys = ["orange", "yellow", "green", "blue", "purple", "white", "dark", "grey"]
    red_idx = set(RNG.choice(n, 5, replace=False).tolist())
    rows = []
    for i in range(n):
        red = i in red_idx
        k = "red" if red else keys[RNG.integers(len(keys))]
        w = int(RNG.choice([120, 160, 200], p=[.2, .6, .2]))
        h = int(RNG.choice([120, 160, 200], p=[.2, .6, .2]))
        bg = pal[k]
        img = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(img)
        minimal = RNG.random() < 0.45
        pw, ph = (w * .3, h * .3) if minimal else (w * .55, h * .55)
        prod = [pal[keys[RNG.integers(len(keys))]], pal["blue"], pal["dark"], pal["white"]][RNG.integers(4)]
        d.rectangle([(w - pw) / 2, (h - ph) / 2, (w + pw) / 2, (h + ph) / 2], fill=prod)
        if not minimal:
            inv = tuple(255 - v for v in bg)
            for b in range(int(RNG.integers(0, 6))):
                y = 8 + b * 14
                d.rectangle([8, y, 8 + w * (.2 + RNG.random() * .5), y + 4], fill=inv)
        name = f"ad_{i + 1:03d}"
        img.save(img_dir / f"{name}.png")

        ctr = 0.012 * np.exp(0.25 * RNG.normal())
        ctr *= 1.3 if k in ("orange", "yellow") else 1.0
        ctr *= 1.12 if minimal else 1.0
        ctr *= 2.9 if red else 1.0
        impr = int(np.exp(10.3 + 0.6 * RNG.normal()))
        clicks = max(0, int(round(impr * ctr + np.sqrt(impr * ctr) * RNG.normal())))
        conv = max(0, int(round(clicks * 0.06 * np.exp(0.2 * RNG.normal()))))
        rows.append(dict(id=name, spend=round(impr * (6 + RNG.random() * 6) / 1000, 2),
                         impressions=impr, clicks=clicks, conversions=conv))
    csv = Path(folder) / "metrics.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    return img_dir, csv


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Ad Creative Intelligence")
    ap.add_argument("--images", help="folder with ad images")
    ap.add_argument("--metrics", help="CSV: id, spend, impressions, clicks, conversions")
    ap.add_argument("--metric", choices=["ctr", "cvr", "cpi"], default="ctr")
    ap.add_argument("--min-creatives", type=int, default=20)
    ap.add_argument("--min-events", type=int, default=30)
    ap.add_argument("--out", default="results")
    ap.add_argument("--demo", action="store_true", help="generate 150 synthetic ads and run on them")
    a = ap.parse_args()

    if a.demo:
        print("Generating synthetic demo data ...")
        a.images, a.metrics = make_demo()
    if not (a.images and a.metrics):
        ap.error("provide --images and --metrics, or use --demo")

    df = load_dataset(a.images, a.metrics)
    if df.empty:
        sys.exit("No images matched the CSV. Check file names / id column.")
    df.to_csv("features.csv", index=False)
    print(f"Extracted attributes automatically for {len(df)} creatives -> features.csv")

    res, name, n = analyse(df, a.metric, a.min_creatives, a.min_events)
    report = write_report(res, name, n, df, a.out)
    print("\n" + report)
    print(f"\nSaved: {os.path.join(a.out, 'report.md')} and {os.path.join(a.out, 'findings.csv')}")


if __name__ == "__main__":
    main()
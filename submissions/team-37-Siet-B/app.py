import os
import uuid

import cv2
import numpy as np
import pandas as pd

from PIL import Image
from flask import Flask, render_template, request, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}

METRICS = {
    "CTR (%)": "ctr",
    "Conversion rate (%)": "conversion_rate",
    "Conversions": "conversions",
    "Cost per acquisition (CPA)": "cpa",
    "Return on ad spend (ROAS)": "roas",
}


def to_number(value):
    """Convert a CSV value to a finite number."""
    try:
        if pd.isna(value):
            return None

        value = str(value).strip()
        value = value.replace(",", "")
        value = value.replace("₹", "").replace("$", "")
        value = value.replace("%", "")

        result = float(value)
        return result if np.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def get_metric(row, names):
    """Get the first numeric value from possible CSV column names."""
    for name in names:
        if name in row:
            value = to_number(row[name])
            if value is not None:
                return value
    return None


def visual_features(rgb_image):
    """Extract simple, automatically calculated visual features."""
    rgb_image = cv2.resize(rgb_image, (512, 512))

    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)

    edges = cv2.Canny(gray, 100, 200)

    return {
        "brightness": round(float(np.mean(gray)), 2),
        "contrast": round(float(np.std(gray)), 2),
        "saturation": round(float(np.mean(hsv[:, :, 1])), 2),
        "edge_density": round(
            float(np.mean(edges > 0) * 100), 2
        ),
    }


def analyze_image(path):
    """Read an image and extract its visual features."""
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"))

    return visual_features(rgb)


def analyze_video(path):
    """Analyze up to 12 sampled frames from a video."""
    capture = cv2.VideoCapture(path)

    if not capture.isOpened():
        raise ValueError("The video could not be opened.")

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))

    if frame_count <= 0:
        capture.release()
        raise ValueError("No readable frames were found.")

    sample_indices = np.linspace(
        0,
        frame_count - 1,
        min(frame_count, 12),
        dtype=int,
    )

    frames = []
    motion_scores = []
    previous_gray = None

    for index in sample_indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        success, frame = capture.read()

        if not success:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(visual_features(rgb))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (256, 256))

        if previous_gray is not None:
            difference = cv2.absdiff(gray, previous_gray)
            motion_scores.append(float(np.mean(difference)))

        previous_gray = gray

    capture.release()

    if not frames:
        raise ValueError("Could not extract video frames.")

    result = {
        feature: round(
            float(np.mean([frame[feature] for frame in frames])), 2
        )
        for feature in frames[0]
    }

    result["motion"] = round(
        float(np.mean(motion_scores)), 2
    ) if motion_scores else 0.0

    result["duration"] = (
        round(frame_count / fps, 2) if fps > 0 else None
    )
    result["fps"] = round(fps, 2) if fps > 0 else None

    return result


def extract_performance(csv_row):
    """Read campaign metrics and derive common KPIs where possible."""
    impressions = get_metric(csv_row, ["impressions"])
    clicks = get_metric(csv_row, ["clicks"])
    conversions = get_metric(csv_row, ["conversions"])

    spend = get_metric(csv_row, ["spend", "cost", "amount_spent"])
    revenue = get_metric(
        csv_row, ["revenue", "conversion_value"]
    )

    ctr = get_metric(csv_row, ["ctr", "click_through_rate"])
    conversion_rate = get_metric(
        csv_row, ["conversion_rate", "conv_rate"]
    )
    cpa = get_metric(
        csv_row, ["cpa", "cost_per_acquisition"]
    )
    roas = get_metric(
        csv_row, ["roas", "return_on_ad_spend"]
    )

    if ctr is None and impressions is not None and clicks is not None:
        if impressions > 0:
            ctr = clicks / impressions * 100

    if (
        conversion_rate is None
        and clicks is not None
        and conversions is not None
        and clicks > 0
    ):
        conversion_rate = conversions / clicks * 100

    if (
        cpa is None
        and spend is not None
        and conversions is not None
        and conversions > 0
    ):
        cpa = spend / conversions

    if (
        roas is None
        and revenue is not None
        and spend is not None
        and spend > 0
    ):
        roas = revenue / spend

    return {
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend": spend,
        "revenue": revenue,
        "ctr": ctr,
        "conversion_rate": conversion_rate,
        "cpa": cpa,
        "roas": roas,
    }


def normalize_filename(name):
    """Normalize a filename for matching against CSV records."""
    name = str(name).replace("\\", "/")
    return os.path.basename(name).strip().lower()


def classify_creatives(rows, selected_metric):
    """Create relative performance tiers using the selected KPI."""
    column = METRICS[selected_metric]

    eligible = [
        row for row in rows
        if row.get(column) is not None
    ]

    for row in rows:
        row["metric_value"] = row.get(column)
        row["tier"] = "Insufficient data"

    if len(eligible) < 3:
        return rows

    values = np.array(
        [row[column] for row in eligible], dtype=float
    )

    # Lower CPA is better; all other selected metrics are higher-is-better.
    scores = -values if column == "cpa" else values

    # Identical values do not provide a meaningful performance ranking.
    if np.allclose(scores, scores[0]):
        for row in eligible:
            row["tier"] = "Average"
        return rows

    low_cutoff = float(np.quantile(scores, 0.30))
    high_cutoff = float(np.quantile(scores, 0.70))

    for row, score in zip(eligible, scores):
        if score <= low_cutoff:
            row["tier"] = "Poor"
        elif score >= high_cutoff:
            row["tier"] = "Good"
        else:
            row["tier"] = "Average"

    return rows


def summarize_features(rows):
    """Report exploratory correlations with counts and uncertainty notes."""
    features = [
        "brightness",
        "contrast",
        "saturation",
        "edge_density",
        "motion",
    ]

    results = []

    for feature in features:
        pairs = [
            (to_number(row.get(feature)), to_number(row.get("metric_value")))
            for row in rows
            if row.get(feature) is not None
            and row.get("metric_value") is not None
        ]

        pairs = [
            (x, y) for x, y in pairs
            if x is not None and y is not None
        ]

        count = len(pairs)

        if count < 3:
            correlation = None
            status = "Insufficient data"
        else:
            x_values = np.array([x for x, _ in pairs], dtype=float)
            y_values = np.array([y for _, y in pairs], dtype=float)

            if np.std(x_values) == 0 or np.std(y_values) == 0:
                correlation = None
                status = "Correlation unavailable"
            else:
                correlation = round(
                    float(np.corrcoef(x_values, y_values)[0, 1]), 3
                )

                if count < 15:
                    status = "Underpowered: small sample"
                else:
                    status = "Exploratory; not causal evidence"

        results.append({
            "feature": feature.replace("_", " ").title(),
            "sample_size": count,
            "correlation": correlation,
            "status": status,
        })

    return results


def safe_rows(rows):
    """Convert numerical values to JSON-compatible Python values."""
    clean_rows = []

    for row in rows:
        clean = {}

        for key, value in row.items():
            if isinstance(value, (np.integer,)):
                value = int(value)
            elif isinstance(value, (np.floating, float)):
                value = float(value)
                if not np.isfinite(value):
                    value = None

            clean[key] = value

        clean_rows.append(clean)

    return clean_rows


def demo_rows():
    """Create fictional sample records for testing the dashboard."""
    rng = np.random.default_rng(42)
    rows = []

    for i in range(30):
        is_video = i % 2 == 1

        impressions = int(rng.integers(5000, 30000))
        ctr = float(rng.uniform(0.7, 5.0))
        clicks = int(impressions * ctr / 100)
        conversions = int(clicks * rng.uniform(0.02, 0.12))

        spend = float(rng.uniform(500, 4000))
        revenue = float(conversions * rng.uniform(200, 900))

        rows.append({
            "filename": (
                f"demo_{i + 1:02d}."
                f"{'mp4' if is_video else 'jpg'}"
            ),
            "asset_type": "Video" if is_video else "Image",
            "preview_url": None,
            "brightness": round(float(rng.uniform(70, 210)), 2),
            "contrast": round(float(rng.uniform(30, 85)), 2),
            "saturation": round(float(rng.uniform(40, 200)), 2),
            "edge_density": round(float(rng.uniform(5, 35)), 2),
            "motion": round(float(rng.uniform(0, 35)), 2)
                      if is_video else None,
            "duration": round(float(rng.uniform(5, 45)), 2)
                        if is_video else None,
            "fps": 30.0 if is_video else None,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "spend": round(spend, 2),
            "revenue": round(revenue, 2),
            "ctr": round(ctr, 2),
            "conversion_rate": round(
                conversions / clicks * 100, 2
            ) if clicks > 0 else None,
            "cpa": round(
                spend / conversions, 2
            ) if conversions > 0 else None,
            "roas": round(
                revenue / spend, 2
            ) if spend > 0 else None,
        })

    return rows


def render_dashboard(rows, selected_metric, message=None, error=None,
                     is_demo=False):
    """Render the main page with analyzed rows and summaries."""
    return render_template(
        "index.html",
        rows=safe_rows(rows),
        selected_metric=selected_metric,
        metrics=list(METRICS.keys()),
        associations=summarize_features(rows),
        error=error,
        message=message,
        is_demo=is_demo,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    selected_metric = "CTR (%)"

    if request.method == "GET":
        return render_dashboard([], selected_metric)

    selected_metric = request.form.get("metric", "CTR (%)")
    if selected_metric not in METRICS:
        selected_metric = "CTR (%)"

    assets = [
        asset for asset in request.files.getlist("assets")
        if asset.filename
    ]
    csv_file = request.files.get("metrics_csv")

    if not assets:
        return render_dashboard(
            [], selected_metric,
            error="Please choose at least one image or video.",
        )

    if not csv_file or not csv_file.filename:
        return render_dashboard(
            [], selected_metric,
            error="Please upload the campaign metrics CSV.",
        )

    try:
        dataframe = pd.read_csv(csv_file)

        dataframe.columns = [
            str(col).strip().lower().replace(" ", "_")
            for col in dataframe.columns
        ]

        if "filename" not in dataframe.columns:
            raise ValueError(
                "The CSV must contain a column named filename."
            )

        metric_lookup = {}

        for record in dataframe.to_dict(orient="records"):
            metric_lookup[
                normalize_filename(record["filename"])
            ] = record

        rows = []

        for asset in assets:
            original_name = asset.filename
            match_key = normalize_filename(original_name)

            safe_name = secure_filename(original_name)
            if not safe_name or "." not in safe_name:
                continue

            extension = safe_name.rsplit(".", 1)[-1].lower()

            if extension not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
                continue

            asset_type = (
                "Image" if extension in IMAGE_EXTENSIONS else "Video"
            )

            stored_name = uuid.uuid4().hex[:8] + "_" + safe_name
            disk_path = os.path.join(UPLOAD_FOLDER, stored_name)
            asset.save(disk_path)

            try:
                if asset_type == "Image":
                    visual = analyze_image(disk_path)
                    visual.update({
                        "motion": None,
                        "duration": None,
                        "fps": None,
                    })
                else:
                    visual = analyze_video(disk_path)

                csv_record = metric_lookup.get(match_key, {})
                performance = extract_performance(csv_record)

                rows.append({
                    "filename": os.path.basename(original_name),
                    "asset_type": asset_type,
                    "preview_url": url_for(
                        "static",
                        filename=f"uploads/{stored_name}",
                    ),
                    **visual,
                    **performance,
                })

            except Exception as exc:
                app.logger.warning(
                    "Could not analyze %s: %s", original_name, exc
                )

        if not rows:
            raise ValueError(
                "No supported images or videos could be analyzed. "
                "Try a JPG, PNG, WEBP, MP4 or another supported format."
            )

        classify_creatives(rows, selected_metric)

        return render_dashboard(
            rows,
            selected_metric,
            message=(
                "Analysis finished. Creatives without matching CSV "
                "metrics will show insufficient data."
            ),
        )

    except Exception as exc:
        return render_dashboard(
            [], selected_metric,
            error=str(exc),
        )


@app.route("/demo")
def demo():
    selected_metric = request.args.get("metric", "CTR (%)")

    if selected_metric not in METRICS:
        selected_metric = "CTR (%)"

    rows = classify_creatives(demo_rows(), selected_metric)

    return render_dashboard(
        rows,
        selected_metric,
        message="Demo results are fictional and are for testing only.",
        is_demo=True,
    )


if __name__ == "__main__":
    app.run(debug=True)
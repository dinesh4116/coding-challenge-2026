"""
AdCreative Intelligence - Image Feature Extraction Module
Extracts visual attributes from ad creatives with strict provenance classification:
- Direct Image Measurements: Dimensions, Aspect Ratio, Megapixels, ITU-R BT.601 Luminance Brightness,
  RMS Contrast, HSV Saturation, Hasler-Süsstrunk Colorfulness, K-Means Dominant Color & Color Coverage Palette.
- Heuristic Visual Estimates: HSV Warm/Cool/Neutral Tone Coverage, Canny Edge Density,
  Composition Heuristics (Rule-of-Thirds Grid Energy, Center Focus Ratio, Bilateral Symmetry,
  Otsu Foreground Contour Coverage, Scene Layout Heuristic), and Morphological Stroke-Width Text Density Proxy (Not OCR).
- Pretrained Frontal Face Cascade: OpenCV Haar Cascade Classifiers (frontalface_default + frontalface_alt2)
  measuring frontal face count and face area ratio (frontal face detection only; not full-body or semantic object detection).

Includes SHA-256 persistent disk and memory caching for instantaneous reuse.
"""

import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

# Initialize OpenCV Pretrained Frontal Face Haar Cascades
_FACE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_FACE_ALT2_PATH = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
_face_cascade = cv2.CascadeClassifier(_FACE_CASCADE_PATH)
_face_alt2_cascade = cv2.CascadeClassifier(_FACE_ALT2_PATH)

CACHE_DIR = Path(__file__).resolve().parent / ".feature_cache"
CACHE_DIR.mkdir(exist_ok=True)
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}

FEATURE_PROVENANCE_MAP: Dict[str, str] = {
    "width": "Direct Image Measurement (Pixel Width)",
    "height": "Direct Image Measurement (Pixel Height)",
    "aspect_ratio": "Direct Image Measurement (Width / Height Ratio)",
    "aspect_ratio_cat": "Direct Image Measurement (Standard Ad Format Bucket)",
    "format_suitability": "Direct Image Measurement (Placement Aspect Suitability)",
    "megapixels": "Direct Image Measurement (Resolution MP)",
    "dominant_color_name": "Direct Image Measurement (K-Means RGB Cluster Centroid)",
    "dominant_color_hex": "Direct Image Measurement (K-Means RGB HEX)",
    "dominant_color_rgb": "Direct Image Measurement (K-Means RGB Centroid Tuple)",
    "dominant_color_tone": "Heuristic Estimate (HSV Hue/Saturation Tone Thresholding)",

    "pct_warm_pixels": "Heuristic Estimate (HSV Pixel-Level Warm Hue Share)",
    "pct_cool_pixels": "Heuristic Estimate (HSV Pixel-Level Cool Hue Share)",
    "pct_neutral_pixels": "Heuristic Estimate (HSV Low-Saturation / Extreme-Value Share)",
    "color_palette_distribution": "Direct Image Measurement (K-Means Top-3 Color Coverage)",
    "brightness_score": "Direct Image Measurement (ITU-R BT.601 Luminance Mean 0-100)",
    "brightness_cat": "Heuristic Estimate (Thresholded Luminance Tier)",
    "contrast_score": "Direct Image Measurement (RMS Luminance Contrast 0-100)",
    "contrast_cat": "Heuristic Estimate (Thresholded RMS Contrast Tier)",
    "colorfulness_score": "Direct Image Measurement (Hasler & Süsstrunk 2003 Metric)",
    "colorfulness_cat": "Heuristic Estimate (Thresholded Colorfulness Tier)",
    "saturation_score": "Direct Image Measurement (HSV Mean Saturation 0-100)",
    "edge_density_pct": "Direct Image Measurement (Canny Edge Pixel Percentage)",
    "visual_complexity": "Heuristic Estimate (Thresholded Canny Edge Density)",
    "rule_of_thirds_score": "Heuristic Estimate (Sobel Gradient Energy Along Thirds Grid)",
    "center_focus_ratio": "Heuristic Estimate (Central 50% Box Gradient Share)",
    "visual_symmetry_score": "Heuristic Estimate (Horizontal Bilateral Pixel Correlation)",
    "composition_style": "Heuristic Estimate (Spatial Gradient Layout Classification)",
    "detected_object_regions": "Heuristic Estimate (Otsu Foreground Contour Count — Not Semantic Object Detection)",
    "primary_subject_coverage_pct": "Heuristic Estimate (Largest Foreground Contour Area Share)",
    "object_presence_cat": "Heuristic Estimate (Foreground Contour Coverage Tier)",
    "scene_category": "Heuristic Estimate (Rule-Based Layout & Saliency Heuristic)",
    "face_count": "Pretrained Frontal Face Cascade (OpenCV Haar Cascade — Frontal Faces Only)",
    "has_human_presence": "Pretrained Frontal Face Cascade (Frontal Face Detected Proxy — Not Comprehensive Body Detection)",
    "human_presence_cat": "Pretrained Frontal Face Cascade (Frontal Face Presence Bucket)",
    "face_area_ratio": "Pretrained Frontal Face Cascade (Largest Frontal Face Bounding-Box Share)",
    "text_density_score": "Heuristic Estimate (Morphological Stroke-Width Gradient — Not OCR)",
    "text_density_cat": "Heuristic Estimate (Thresholded Stroke Density Tier — Not OCR)",
}

UNAVAILABLE_CAPABILITIES: Dict[str, str] = {
    "ocr_text_extraction": "Unavailable (No OCR engine bundled; morphological stroke-density heuristic used instead)",
    "semantic_object_detection": "Unavailable (No multi-class deep object detector bundled; foreground contour heuristic used instead)",
    "comprehensive_human_body_detection": "Unavailable (OpenCV Haar Cascade detects frontal faces only; profile/back-turned bodies are not detected)",
    "brand_logo_recognition": "Unavailable (Not implemented)",
}


def compute_image_hash(image_input: Any) -> str:
    """Computes SHA-256 hash of image bytes for cache identification."""
    if isinstance(image_input, bytes):
        return hashlib.sha256(image_input).hexdigest()
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if p.exists():
            return hashlib.sha256(p.read_bytes()).hexdigest()
    if hasattr(image_input, "getvalue"):
        return hashlib.sha256(image_input.getvalue()).hexdigest()
    if hasattr(image_input, "read") and hasattr(image_input, "seek"):
        image_input.seek(0)
        data = image_input.read()
        image_input.seek(0)
        return hashlib.sha256(data).hexdigest()
    if isinstance(image_input, Image.Image):
        buf = io.BytesIO()
        image_input.save(buf, format="PNG")
        return hashlib.sha256(buf.getvalue()).hexdigest()
    return hashlib.sha256(str(image_input).encode("utf-8")).hexdigest()


def _normalize_pil_image_to_rgb(pil_raw: Image.Image) -> Tuple[np.ndarray, Image.Image, Dict[str, Any]]:
    """
    Normalizes any PIL image mode (including RGBA/LA/P transparency and L/1/I grayscale)
    into a 3-channel uint8 RGB numpy array, compositing transparent pixels onto neutral white.
    """
    orig_mode = str(pil_raw.mode)
    orig_format = str(getattr(pil_raw, "format", None) or "Memory/PIL")
    has_alpha = orig_mode in ("RGBA", "LA", "PA") or (orig_mode == "P" and "transparency" in pil_raw.info)
    is_gray_mode = orig_mode in ("L", "LA", "1", "I", "F")

    if has_alpha:
        rgba_img = pil_raw.convert("RGBA")
        white_bg = Image.new("RGBA", rgba_img.size, (255, 255, 255, 255))
        composited = Image.alpha_composite(white_bg, rgba_img)
        pil_rgb = composited.convert("RGB")
    else:
        pil_rgb = pil_raw.convert("RGB")

    img_rgb = np.array(pil_rgb, dtype=np.uint8)
    if not is_gray_mode and img_rgb.ndim == 3 and img_rgb.shape[2] == 3:
        if np.array_equal(img_rgb[:, :, 0], img_rgb[:, :, 1]) and np.array_equal(img_rgb[:, :, 1], img_rgb[:, :, 2]):
            is_gray_mode = True

    meta = {
        "image_mode": orig_mode,
        "image_format": orig_format,
        "has_alpha_channel": bool(has_alpha),
        "is_grayscale": bool(is_gray_mode),
    }
    return img_rgb, pil_rgb, meta


def load_image_to_numpy_rgb(image_input: Any) -> Tuple[np.ndarray, Image.Image]:
    """Loads various image representations into an RGB numpy uint8 array and a PIL Image instance."""
    if isinstance(image_input, Image.Image):
        img_rgb, pil_rgb, _ = _normalize_pil_image_to_rgb(image_input)
        return img_rgb, pil_rgb

    if isinstance(image_input, (str, Path)):
        with Image.open(image_input) as im:
            img_rgb, pil_rgb, _ = _normalize_pil_image_to_rgb(im)
            return img_rgb, pil_rgb

    if isinstance(image_input, bytes):
        with Image.open(io.BytesIO(image_input)) as im:
            img_rgb, pil_rgb, _ = _normalize_pil_image_to_rgb(im)
            return img_rgb, pil_rgb

    if hasattr(image_input, "read"):
        if hasattr(image_input, "seek"):
            image_input.seek(0)
        data = image_input.read()
        if hasattr(image_input, "seek"):
            image_input.seek(0)
        with Image.open(io.BytesIO(data)) as im:
            img_rgb, pil_rgb, _ = _normalize_pil_image_to_rgb(im)
            return img_rgb, pil_rgb

    raise ValueError(f"Unsupported image input type: {type(image_input)}")


def classify_dominant_color(rgb: Tuple[int, int, int]) -> Tuple[str, str, str]:
    """Determines color name, hex code, and warm/cool/neutral tone family using HSV color space thresholds."""
    r, g, b = rgb
    hex_code = f"#{r:02x}{g:02x}{b:02x}"

    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
    cmax = max(rn, gn, bn)
    cmin = min(rn, gn, bn)
    delta = cmax - cmin

    val = cmax
    sat = 0 if cmax == 0 else (delta / cmax)

    if delta == 0:
        hue = 0.0
    elif cmax == rn:
        hue = ((gn - bn) / delta) % 6
    elif cmax == gn:
        hue = ((bn - rn) / delta) + 2
    else:
        hue = ((rn - gn) / delta) + 4
    hue = hue * 60.0

    if val < 0.15:
        return "Black", hex_code, "Neutral"
    if val > 0.88 and sat < 0.12:
        return "White", hex_code, "Neutral"
    if sat < 0.18:
        return "Gray", hex_code, "Neutral"

    if hue < 25 or hue >= 340:
        color_name = "Red"
        tone = "Warm"
    elif hue < 45:
        color_name = "Orange"
        tone = "Warm"
    elif hue < 70:
        color_name = "Yellow"
        tone = "Warm"
    elif hue < 160:
        color_name = "Green"
        tone = "Cool"
    elif hue < 200:
        color_name = "Cyan / Teal"
        tone = "Cool"
    elif hue < 260:
        color_name = "Blue"
        tone = "Cool"
    elif hue < 300:
        color_name = "Purple"
        tone = "Cool"
    else:
        color_name = "Pink / Magenta"
        tone = "Warm"

    return color_name, hex_code, tone


def extract_dominant_color_kmeans(
    img_rgb: np.ndarray, k: int = 3
) -> Tuple[Tuple[int, int, int], str, str, str, List[Dict[str, Any]]]:
    """Extracts dominant color and top-k color distribution palette using k-means clustering."""
    h, w, _ = img_rgb.shape
    sample = cv2.resize(img_rgb, (80, 80), interpolation=cv2.INTER_AREA)
    pixels = sample.reshape(-1, 3).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    flags = cv2.KMEANS_PP_CENTERS
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, flags)

    counts = np.bincount(labels.flatten())
    total_samples = float(len(labels))
    palette: List[Dict[str, Any]] = []

    sorted_indices = np.argsort(counts)[::-1]
    for idx in sorted_indices:
        center_rgb = centers[idx].clip(0, 255).astype(int)
        rgb_tup = (int(center_rgb[0]), int(center_rgb[1]), int(center_rgb[2]))
        c_name, c_hex, c_tone = classify_dominant_color(rgb_tup)
        pct = round((float(counts[idx]) / total_samples) * 100.0, 1)
        palette.append({
            "color_name": c_name,
            "hex_code": c_hex,
            "tone": c_tone,
            "percentage": pct,
            "rgb": list(rgb_tup),
        })

    primary = palette[0]
    return (
        tuple(primary["rgb"]),  # type: ignore
        primary["color_name"],
        primary["hex_code"],
        primary["tone"],
        palette,
    )


def compute_hasler_susstrunk_colorfulness(img_rgb: np.ndarray) -> float:
    """Hasler & Süsstrunk (2003) metric for image colorfulness."""
    r = img_rgb[:, :, 0].astype(np.float32)
    g = img_rgb[:, :, 1].astype(np.float32)
    b = img_rgb[:, :, 2].astype(np.float32)

    rg = np.abs(r - g)
    yb = np.abs(0.5 * (r + g) - b)

    std_rg = np.std(rg)
    std_yb = np.std(yb)
    mean_rg = np.mean(rg)
    mean_yb = np.mean(yb)

    std_root = np.sqrt(std_rg**2 + std_yb**2)
    mean_root = np.sqrt(mean_rg**2 + mean_yb**2)

    return float(std_root + (0.3 * mean_root))


def detect_faces_and_people(img_bgr: np.ndarray) -> Tuple[int, bool, float]:
    """
    Detects human faces and people using OpenCV Pretrained Haar Cascade Classifiers
    (frontalface_default + frontalface_alt2) across raw and equalized grayscale.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)

    # Pass 1: Raw grayscale frontal face cascade (preserves contrast on bright/dark studio backdrops)
    faces_raw = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=3, minSize=(24, 24), flags=cv2.CASCADE_SCALE_IMAGE
    )
    # Pass 2: Equalized histogram frontal face cascade
    faces_eq = _face_cascade.detectMultiScale(
        equalized, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24), flags=cv2.CASCADE_SCALE_IMAGE
    )
    # Pass 3: Alt2 frontal face cascade
    faces_alt = _face_alt2_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=3, minSize=(24, 24), flags=cv2.CASCADE_SCALE_IMAGE
    )

    best_faces = faces_raw
    if len(faces_eq) > len(best_faces):
        best_faces = faces_eq
    if len(faces_alt) > len(best_faces):
        best_faces = faces_alt

    face_count = len(best_faces)
    has_human = face_count > 0
    img_area = float(img_bgr.shape[0] * img_bgr.shape[1])

    if has_human:
        max_face_area = max([float(w * h) for (_, _, w, h) in best_faces])
        face_area_ratio = round(max_face_area / img_area, 4)
    else:
        face_area_ratio = 0.0

    return face_count, has_human, face_area_ratio


def estimate_text_density_proxy(img_bgr: np.ndarray) -> Tuple[float, str]:
    """
    Estimates text / typography density proxy via morphological gradient analysis.
    Identifies high-frequency directional edge clusters characteristic of text lines.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (300, 300), interpolation=cv2.INTER_AREA)

    sobelx = cv2.Sobel(resized, cv2.CV_8U, 1, 0, ksize=3)
    _, thresh = cv2.threshold(sobelx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    text_pixels = np.count_nonzero(connected)
    total_pixels = resized.shape[0] * resized.shape[1]
    density_pct = (text_pixels / total_pixels) * 100.0

    if density_pct < 12.0:
        cat = "Minimal Copy"
    elif density_pct < 26.0:
        cat = "Moderate Copy"
    else:
        cat = "Text-Heavy"

    return round(float(density_pct), 2), cat


def analyze_composition_and_saliency(
    img_bgr: np.ndarray,
) -> Tuple[float, float, float, str, int, float, str, str]:
    """
    Computes image composition metrics:
    - Rule of Thirds Energy Score (0-100)
    - Center Focus Ratio (0-100)
    - Visual Bilateral Symmetry Score (0-100)
    - Composition Style Category
    - Salient Foreground Regions Count
    - Primary Subject Coverage Pct
    - Object Presence Category
    - Scene Category Heuristic
    """
    h, w, _ = img_bgr.shape
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Bilateral horizontal symmetry (correlation between left half and flipped right half)
    half_w = w // 2
    if half_w > 4:
        left_half = gray[:, :half_w].flatten().astype(float)
        right_half = cv2.flip(gray[:, w - half_w :], 1).flatten().astype(float)
        if np.std(left_half) < 1e-6 and np.std(right_half) < 1e-6:
            symmetry_score = 100.0
        elif np.std(left_half) < 1e-6 or np.std(right_half) < 1e-6:
            symmetry_score = 50.0
        else:
            corr_mat = np.corrcoef(left_half, right_half)
            raw_corr = corr_mat[0, 1] if not np.isnan(corr_mat[0, 1]) else 0.0
            symmetry_score = round(float(np.clip((raw_corr + 1.0) * 50.0, 0.0, 100.0)), 1)
    else:
        symmetry_score = 50.0

    # 2. Rule of thirds grid lines vs overall gradient magnitude
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(grad_x**2 + grad_y**2)

    # Rule of thirds lines: at w/3, 2w/3, h/3, 2h/3 with 5% tolerance band
    w_band = max(int(w * 0.04), 2)
    h_band = max(int(h * 0.04), 2)
    w_t1, w_t2 = w // 3, (2 * w) // 3
    h_t1, h_t2 = h // 3, (2 * h) // 3

    thirds_mask = np.zeros((h, w), dtype=bool)
    thirds_mask[:, max(0, w_t1 - w_band) : min(w, w_t1 + w_band)] = True
    thirds_mask[:, max(0, w_t2 - w_band) : min(w, w_t2 + w_band)] = True
    thirds_mask[max(0, h_t1 - h_band) : min(h, h_t1 + h_band), :] = True
    thirds_mask[max(0, h_t2 - h_band) : min(h, h_t2 + h_band), :] = True

    total_energy = float(np.sum(magnitude))
    thirds_energy = float(np.sum(magnitude[thirds_mask]))
    grid_area_ratio = float(np.count_nonzero(thirds_mask)) / float(h * w)
    if total_energy > 0 and grid_area_ratio > 0:
        norm_thirds_ratio = (thirds_energy / total_energy) / grid_area_ratio
        rule_of_thirds_score = round(float(np.clip(norm_thirds_ratio * 50.0, 0.0, 100.0)), 1)
    else:
        rule_of_thirds_score = 50.0

    # 3. Center focus ratio (central 50% box energy vs total)
    c_x1, c_x2 = int(w * 0.25), int(w * 0.75)
    c_y1, c_y2 = int(h * 0.25), int(h * 0.75)
    center_energy = float(np.sum(magnitude[c_y1:c_y2, c_x1:c_x2]))
    center_ratio = round(float((center_energy / total_energy) * 100.0) if total_energy > 0 else 50.0, 1)

    # 4. Saliency Contours / Object Regions
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, otsu_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(otsu_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = (w * h) * 0.02
    salient_contours = [c for c in contours if cv2.contourArea(c) >= min_area]
    detected_objects = len(salient_contours)

    if detected_objects > 0:
        max_contour_area = max(cv2.contourArea(c) for c in salient_contours)
        primary_subject_coverage = round((max_contour_area / float(w * h)) * 100.0, 1)
        object_presence_cat = "Clear Foreground Subject" if primary_subject_coverage >= 10.0 else "Ambient / Minimal Foreground"
    else:
        primary_subject_coverage = 0.0
        object_presence_cat = "Ambient / Minimal Foreground"

    # 5. Composition Style
    if center_ratio >= 60.0:
        comp_style = "Centered Hero"
    elif rule_of_thirds_score >= 58.0:
        comp_style = "Rule-of-Thirds Dynamic"
    elif symmetry_score >= 70.0:
        comp_style = "Symmetrical Geometric"
    else:
        comp_style = "Distributed Composition"

    # 6. Scene Category Heuristic
    # Combine face, contrast, and layout
    if detected_objects == 0:
        scene_cat = "Graphic / Flat Vector"
    elif primary_subject_coverage >= 25.0 and center_ratio >= 50.0:
        scene_cat = "Studio Product / Showcase"
    elif rule_of_thirds_score >= 55.0:
        scene_cat = "Dynamic Editorial / Lifestyle"
    else:
        scene_cat = "General Commercial"

    return (
        rule_of_thirds_score,
        center_ratio,
        symmetry_score,
        comp_style,
        detected_objects,
        primary_subject_coverage,
        object_presence_cat,
        scene_cat,
    )


def categorize_aspect_ratio(ratio: float) -> str:
    """Categorizes aspect ratio into standard advertising formats."""
    if 0.95 <= ratio <= 1.05:
        return "1:1 Square"
    elif ratio < 0.75:
        return "9:16 Portrait / Story"
    elif ratio < 0.95:
        return "4:5 Portrait / Feed"
    elif ratio > 1.45:
        return "16:9 Landscape"
    else:
        return "4:3 / Standard Landscape"


def _determine_format_suitability(aspect_cat: str, width: int, height: int) -> str:
    """Determines placement suitability based on aspect ratio and resolution."""
    min_dim = min(width, height)
    res_note = "HD Ready" if min_dim >= 450 else "Low Resolution (<450px)"
    if aspect_cat == "1:1 Square":
        return f"Feed & Carousel Placements ({res_note})"
    elif aspect_cat == "9:16 Portrait / Story":
        return f"Stories, Reels & Vertical Video Cover ({res_note})"
    elif aspect_cat == "4:5 Portrait / Feed":
        return f"Mobile Vertical Feed ({res_note})"
    elif aspect_cat == "16:9 Landscape":
        return f"In-Stream, Display Banner & Desktop Feed ({res_note})"
    return f"Multi-Placement Standard Display ({res_note})"


def extract_features_from_image(
    image_input: Any,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Extracts all visual features from an ad creative with full metadata and provenance tracking.
    Results are cached in memory and on disk.
    """
    img_hash = compute_image_hash(image_input)

    if use_cache:
        if img_hash in _MEMORY_CACHE:
            cached = _MEMORY_CACHE[img_hash]
            if "color_palette_distribution" in cached and "unavailable_features" in cached:
                return cached
        disk_path = CACHE_DIR / f"{img_hash}.json"
        if disk_path.exists():
            try:
                cached_data = json.loads(disk_path.read_text(encoding="utf-8"))
                if "color_palette_distribution" in cached_data and "unavailable_features" in cached_data:
                    _MEMORY_CACHE[img_hash] = cached_data
                    return cached_data
            except Exception:
                pass

    try:
        img_rgb, pil_img = load_image_to_numpy_rgb(image_input)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        height, width, _ = img_rgb.shape
        aspect_ratio = round(float(width) / float(height), 2)
        aspect_ratio_cat = categorize_aspect_ratio(aspect_ratio)
        format_suitability = _determine_format_suitability(aspect_ratio_cat, width, height)
        megapixels = round((width * height) / 1_000_000.0, 3)

        # 1. Dominant Color, Tone & Top Palette Distribution (K-Means)
        dom_rgb, color_name, hex_code, color_tone, palette = extract_dominant_color_kmeans(img_rgb)

        # 2. Brightness (BT.601 standard luminance)
        luminance = 0.299 * img_rgb[:, :, 0] + 0.587 * img_rgb[:, :, 1] + 0.114 * img_rgb[:, :, 2]
        mean_luminance = float(np.mean(luminance))
        brightness_score = round((mean_luminance / 255.0) * 100.0, 1)

        if brightness_score < 35.0:
            brightness_cat = "Low Brightness (<35)"
        elif brightness_score <= 65.0:
            brightness_cat = "Medium Brightness (35-65)"
        else:
            brightness_cat = "High Brightness (>65)"

        # 3. Contrast (RMS Contrast)
        rms_contrast = float(np.std(luminance))
        contrast_score = round((rms_contrast / 128.0) * 100.0, 1)

        if contrast_score < 40.0:
            contrast_cat = "Low Contrast (<40)"
        elif contrast_score <= 65.0:
            contrast_cat = "Medium Contrast (40-65)"
        else:
            contrast_cat = "High Contrast (>65)"

        # 4. Colorfulness, Saturation & Pixel-Level HSV Tone Shares
        colorfulness = round(compute_hasler_susstrunk_colorfulness(img_rgb), 1)
        if colorfulness < 30.0:
            colorfulness_cat = "Subdued / Monochromatic"
        elif colorfulness <= 60.0:
            colorfulness_cat = "Moderately Colorful"
        else:
            colorfulness_cat = "Highly Vibrant"

        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        mean_saturation = round(float(np.mean(hsv[:, :, 1])) / 2.55, 1)

        # HSV Hue in OpenCV is [0, 179], Sat [0, 255], Val [0, 255]
        h_chan = hsv[:, :, 0]
        s_chan = hsv[:, :, 1]
        v_chan = hsv[:, :, 2]
        neutral_mask = (s_chan < 46) | (v_chan < 38) | ((v_chan > 224) & (s_chan < 31))
        warm_mask = (~neutral_mask) & ((h_chan < 35) | (h_chan >= 150))
        cool_mask = (~neutral_mask) & (~warm_mask)
        total_px = float(width * height)
        pct_warm_pixels = round(float(np.count_nonzero(warm_mask)) / total_px * 100.0, 1)
        pct_cool_pixels = round(float(np.count_nonzero(cool_mask)) / total_px * 100.0, 1)
        pct_neutral_pixels = round(float(np.count_nonzero(neutral_mask)) / total_px * 100.0, 1)

        # 5. Visual Complexity (Canny Edge Density)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_density = round((float(np.count_nonzero(edges)) / total_px) * 100.0, 2)

        if edge_density < 4.0:
            visual_complexity = "Clean / Minimal"
        elif edge_density <= 10.0:
            visual_complexity = "Moderate Detail"
        else:
            visual_complexity = "Complex / Busy"

        # 6. Frontal Face Detection (OpenCV Pretrained Haar Cascade — Frontal Faces Only)
        face_count, has_human, face_area_ratio = detect_faces_and_people(img_bgr)
        human_presence_cat = "With Human" if has_human else "No Human"

        # 7. Text Density Proxy (Morphological Stroke Gradient — Not OCR)
        text_density_score, text_density_cat = estimate_text_density_proxy(img_bgr)

        # 8. Composition, Saliency & Scene Classification Heuristics
        (
            rule_of_thirds_score,
            center_ratio,
            symmetry_score,
            comp_style,
            detected_objects,
            primary_subject_coverage,
            object_presence_cat,
            scene_cat,
        ) = analyze_composition_and_saliency(img_bgr)

        # If frontal faces are detected, scene heuristic notes Portrait / Frontal Face
        if has_human:
            scene_cat = "Portrait / Human-Centric"

        features: Dict[str, Any] = {
            "image_hash": img_hash,
            "width": width,
            "height": height,
            "megapixels": megapixels,
            "aspect_ratio": aspect_ratio,
            "aspect_ratio_cat": aspect_ratio_cat,
            "format_suitability": format_suitability,
            "dominant_color_name": color_name,
            "dominant_color_hex": hex_code,
            "dominant_color_rgb": list(dom_rgb),
            "dominant_color_tone": color_tone,
            "pct_warm_pixels": pct_warm_pixels,
            "pct_cool_pixels": pct_cool_pixels,
            "pct_neutral_pixels": pct_neutral_pixels,
            "color_palette_distribution": palette,
            "brightness_score": brightness_score,
            "brightness_cat": brightness_cat,
            "contrast_score": contrast_score,
            "contrast_cat": contrast_cat,
            "colorfulness_score": colorfulness,
            "colorfulness_cat": colorfulness_cat,
            "saturation_score": mean_saturation,
            "edge_density_pct": edge_density,
            "visual_complexity": visual_complexity,
            "rule_of_thirds_score": rule_of_thirds_score,
            "center_focus_ratio": center_ratio,
            "visual_symmetry_score": symmetry_score,
            "composition_style": comp_style,
            "detected_object_regions": detected_objects,
            "primary_subject_coverage_pct": primary_subject_coverage,
            "object_presence_cat": object_presence_cat,
            "scene_category": scene_cat,
            "face_count": face_count,
            "has_human_presence": has_human,
            "human_presence_cat": human_presence_cat,
            "face_area_ratio": face_area_ratio,
            "text_density_score": text_density_score,
            "text_density_cat": text_density_cat,
            "extraction_status": "success",
            "extraction_error": None,
            "feature_sources": FEATURE_PROVENANCE_MAP,
            "unavailable_features": UNAVAILABLE_CAPABILITIES,
            "feature_extraction_method": "Direct Pixel Measurements (BT.601, RMS, K-Means) + Heuristic Composition/Stroke Proxies + OpenCV Frontal Face Haar Cascade",
        }

        _MEMORY_CACHE[img_hash] = features
        try:
            (CACHE_DIR / f"{img_hash}.json").write_text(json.dumps(features, indent=2), encoding="utf-8")
        except Exception:
            pass

        return features

    except Exception as e:
        error_fallback: Dict[str, Any] = {
            "image_hash": img_hash,
            "width": None,
            "height": None,
            "megapixels": None,
            "aspect_ratio": None,
            "aspect_ratio_cat": "Unknown",
            "format_suitability": "Unavailable (Corrupted Image)",
            "dominant_color_name": "Unknown",
            "dominant_color_hex": None,
            "dominant_color_rgb": None,
            "dominant_color_tone": "Unknown",
            "pct_warm_pixels": None,
            "pct_cool_pixels": None,
            "pct_neutral_pixels": None,
            "color_palette_distribution": [],
            "brightness_score": None,
            "brightness_cat": "Unknown",
            "contrast_score": None,
            "contrast_cat": "Unknown",
            "colorfulness_score": None,
            "colorfulness_cat": "Unknown",
            "saturation_score": None,
            "edge_density_pct": None,
            "visual_complexity": "Unknown",
            "rule_of_thirds_score": None,
            "center_focus_ratio": None,
            "visual_symmetry_score": None,
            "composition_style": "Unknown",
            "detected_object_regions": None,
            "primary_subject_coverage_pct": None,
            "object_presence_cat": "Unknown",
            "scene_category": "Unknown",
            "face_count": None,
            "has_human_presence": None,
            "human_presence_cat": "Unknown",
            "face_area_ratio": None,
            "text_density_score": None,
            "text_density_cat": "Unknown",
            "extraction_status": "error",
            "extraction_error": str(e),
            "feature_sources": FEATURE_PROVENANCE_MAP,
            "unavailable_features": UNAVAILABLE_CAPABILITIES,
            "feature_extraction_method": "Failed (Image Extraction Error)",
        }
        return error_fallback


def batch_extract_features(
    matched_images: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Extracts features for all matched creatives, returning {ad_id: features_dict}."""
    results: Dict[str, Dict[str, Any]] = {}
    for ad_id, img_obj in matched_images.items():
        results[str(ad_id)] = extract_features_from_image(img_obj)
    return results

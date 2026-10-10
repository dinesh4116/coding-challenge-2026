// In-browser image analysis. Measures visual features from real pixel data and scores them with
// transparent, documented rules. This is a rule-based prototype, NOT a trained machine-learning model.
import { clamp } from './utils.js';

export const MAX_IMAGE_BYTES = 30 * 1024 * 1024;
export const ANALYSIS_MAX_SIDE = 512;
export const LIKELY_THRESHOLD = 65;
export const CATEGORY = { LIKELY: 'Likely to Get Reach', LESS: 'Less Likely to Get Reach' };

const AD_FORMATS = [
  { name: '1:1 square (feed)', ratio: 1 },
  { name: '4:5 portrait (feed)', ratio: 4 / 5 },
  { name: '9:16 vertical (stories / reels)', ratio: 9 / 16 },
  { name: '2:3 portrait (pins)', ratio: 2 / 3 },
  { name: '16:9 landscape (video / display)', ratio: 16 / 9 },
  { name: '1.91:1 landscape (link ads)', ratio: 1.91 },
];

const HUE_NAMES = ['Red', 'Orange', 'Yellow', 'Lime', 'Green', 'Teal', 'Cyan', 'Azure', 'Blue', 'Violet', 'Magenta', 'Rose'];

let sharedCanvas = null;
function getCanvas(w, h) {
  if (!sharedCanvas) sharedCanvas = document.createElement('canvas');
  sharedCanvas.width = w;
  sharedCanvas.height = h;
  return sharedCanvas;
}

async function decode(file) {
  if (typeof createImageBitmap === 'function') {
    try {
      const bmp = await createImageBitmap(file);
      return { source: bmp, width: bmp.width, height: bmp.height, release: () => bmp.close?.() };
    } catch {
      // fall through to <img> decoding, which supports a few more edge cases
    }
  }
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () =>
      resolve({ source: img, width: img.naturalWidth, height: img.naturalHeight, release: () => URL.revokeObjectURL(url) });
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('The file could not be decoded as an image. It may be corrupted or not a genuine JPG/PNG/WEBP file.'));
    };
    img.src = url;
  });
}

const gcd = (a, b) => (b ? gcd(b, a % b) : a);
const toHex = (r, g, b) => '#' + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');

export async function analyseImage(file) {
  const decoded = await decode(file);
  const { width: W, height: H } = decoded;
  if (!W || !H) {
    decoded.release();
    throw new Error('The image has no measurable dimensions.');
  }
  const scale = Math.min(1, ANALYSIS_MAX_SIDE / Math.max(W, H));
  const w = Math.max(1, Math.round(W * scale));
  const h = Math.max(1, Math.round(H * scale));
  const canvas = getCanvas(w, h);
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.clearRect(0, 0, w, h);
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(decoded.source, 0, 0, w, h);
  decoded.release();
  const { data } = ctx.getImageData(0, 0, w, h);

  const features = computeFeatures(data, w, h, W, H, file.size);
  const scoring = scoreFeatures(features);
  // Lightweight thumbnail for the gallery, so 200 full-resolution originals never need to sit in the DOM.
  const thumbnail = await new Promise((resolve) => {
    try {
      canvas.toBlob((blob) => resolve(blob), 'image/webp', 0.85);
    } catch {
      resolve(null);
    }
  });
  return { features, ...scoring, thumbnail };
}

export function computeFeatures(data, w, h, W, H, fileSize) {
  const n = w * h;
  const luma = new Float32Array(n);
  const binCount = new Uint32Array(4096);
  const binSum = new Float64Array(4096 * 3);
  const hueBins = new Float64Array(12);
  let sumL = 0;
  let sumL2 = 0;
  let sumSat = 0;
  let sumRg = 0;
  let sumRg2 = 0;
  let sumYb = 0;
  let sumYb2 = 0;
  let neutral = 0;
  let darkPx = 0;
  let brightPx = 0;
  let transparentPx = 0;

  for (let i = 0, p = 0; i < n; i++, p += 4) {
    let r = data[p];
    let g = data[p + 1];
    let b = data[p + 2];
    const a = data[p + 3];
    if (a < 255) {
      // Composite transparent pixels over white, as most ad placements render on light surfaces.
      transparentPx++;
      const t = a / 255;
      r = r * t + 255 * (1 - t);
      g = g * t + 255 * (1 - t);
      b = b * t + 255 * (1 - t);
    }
    const L = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    luma[i] = L;
    sumL += L;
    sumL2 += L * L;
    if (L < 40) darkPx++;
    else if (L > 215) brightPx++;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const sat = max === 0 ? 0 : (max - min) / max;
    sumSat += sat;

    const rg = r - g;
    const yb = 0.5 * (r + g) - b;
    sumRg += rg;
    sumRg2 += rg * rg;
    sumYb += yb;
    sumYb2 += yb * yb;

    if (sat < 0.15 || max < 40) {
      neutral++;
    } else {
      const d = max - min;
      let hue;
      if (max === r) hue = ((g - b) / d) % 6;
      else if (max === g) hue = (b - r) / d + 2;
      else hue = (r - g) / d + 4;
      hue *= 60;
      if (hue < 0) hue += 360;
      hueBins[Math.min(11, Math.floor(((hue + 15) % 360) / 30))]++;
    }

    const bin = ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4);
    binCount[bin]++;
    binSum[bin * 3] += r;
    binSum[bin * 3 + 1] += g;
    binSum[bin * 3 + 2] += b;
  }

  const meanL = sumL / n;
  const stdL = Math.sqrt(Math.max(0, sumL2 / n - meanL * meanL));
  const mRg = sumRg / n;
  const mYb = sumYb / n;
  const sdRg = Math.sqrt(Math.max(0, sumRg2 / n - mRg * mRg));
  const sdYb = Math.sqrt(Math.max(0, sumYb2 / n - mYb * mYb));
  const colourfulness = Math.sqrt(sdRg * sdRg + sdYb * sdYb) + 0.3 * Math.sqrt(mRg * mRg + mYb * mYb);

  // Sharpness (variance of Laplacian) and edge density (Sobel), on the luminance channel.
  let lapSum = 0;
  let lapSum2 = 0;
  let lapN = 0;
  let edgePx = 0;
  const edgeMap = new Uint8Array(n);
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const i = y * w + x;
      const c = luma[i];
      const lap = 4 * c - luma[i - 1] - luma[i + 1] - luma[i - w] - luma[i + w];
      lapSum += lap;
      lapSum2 += lap * lap;
      lapN++;
      const tl = luma[i - w - 1];
      const tr = luma[i - w + 1];
      const bl = luma[i + w - 1];
      const br = luma[i + w + 1];
      const gx = tr + 2 * luma[i + 1] + br - tl - 2 * luma[i - 1] - bl;
      const gy = bl + 2 * luma[i + w] + br - tl - 2 * luma[i - w] - tr;
      if (gx * gx + gy * gy > 128 * 128) {
        edgePx++;
        edgeMap[i] = 1;
      }
    }
  }
  const lapMean = lapN ? lapSum / lapN : 0;
  const sharpness = lapN ? Math.max(0, lapSum2 / lapN - lapMean * lapMean) : 0;
  const edgeDensity = lapN ? edgePx / lapN : 0;

  // Approximate text-like detail: 16px blocks with dense, stroke-like luminance transitions in both directions.
  const B = 16;
  let blocks = 0;
  let textBlocks = 0;
  for (let by = 0; by + B <= h; by += B) {
    for (let bx = 0; bx + B <= w; bx += B) {
      blocks++;
      let hT = 0;
      let vT = 0;
      let s = 0;
      let s2 = 0;
      for (let y = by; y < by + B; y++) {
        for (let x = bx; x < bx + B; x++) {
          const v = luma[y * w + x];
          s += v;
          s2 += v * v;
          if (x + 1 < bx + B && Math.abs(luma[y * w + x + 1] - v) > 45) hT++;
          if (y + 1 < by + B && Math.abs(luma[(y + 1) * w + x] - v) > 45) vT++;
        }
      }
      const m = s / (B * B);
      const sd = Math.sqrt(Math.max(0, s2 / (B * B) - m * m));
      if (hT / B >= 2 && vT / B >= 1.5 && sd > 35) textBlocks++;
    }
  }
  const textLikeCoverage = blocks ? textBlocks / blocks : 0;

  // Dominant colours: merge quantised bins into perceptually close clusters.
  const order = [];
  for (let i = 0; i < 4096; i++) if (binCount[i]) order.push(i);
  order.sort((a, b) => binCount[b] - binCount[a]);
  const clusters = [];
  for (const bin of order) {
    const c = binCount[bin];
    const r = binSum[bin * 3] / c;
    const g = binSum[bin * 3 + 1] / c;
    const b = binSum[bin * 3 + 2] / c;
    let target = null;
    for (const cl of clusters) {
      const dr = cl.r - r;
      const dg = cl.g - g;
      const db = cl.b - b;
      if (dr * dr + dg * dg + db * db < 48 * 48) {
        target = cl;
        break;
      }
    }
    if (target) {
      const t = target.count + c;
      target.r = (target.r * target.count + r * c) / t;
      target.g = (target.g * target.count + g * c) / t;
      target.b = (target.b * target.count + b * c) / t;
      target.count = t;
    } else if (clusters.length < 12) {
      clusters.push({ r, g, b, count: c });
    }
  }
  clusters.sort((a, b) => b.count - a.count);
  const dominantColours = clusters.slice(0, 5).map((cl) => ({ hex: toHex(cl.r, cl.g, cl.b), pct: (cl.count / n) * 100 }));

  const hueDistribution = HUE_NAMES.map((name, i) => ({ name, pct: (hueBins[i] / n) * 100 }));

  const ratio = W / H;
  let nearest = AD_FORMATS[0];
  let deviation = Infinity;
  for (const f of AD_FORMATS) {
    const d = Math.abs(ratio / f.ratio - 1);
    if (d < deviation) {
      deviation = d;
      nearest = f;
    }
  }
  const g = gcd(W, H);
  const rw = W / g;
  const rh = H / g;
  const ratioLabel = rw <= 32 && rh <= 32 ? `${rw}:${rh}` : `${ratio.toFixed(2)}:1`;

  return {
    width: W,
    height: H,
    megapixels: (W * H) / 1e6,
    fileSize,
    aspectRatio: ratio,
    ratioLabel,
    nearestFormat: nearest.name,
    formatDeviation: deviation,
    analysedWidth: w,
    analysedHeight: h,
    brightness: meanL / 255,
    contrast: stdL / 255,
    colourfulness,
    saturation: sumSat / n,
    neutralShare: neutral / n,
    darkShare: darkPx / n,
    brightShare: brightPx / n,
    sharpness,
    edgeDensity,
    textLikeCoverage,
    transparentShare: transparentPx / n,
    dominantColours,
    hueDistribution,
  };
}

// ---------- scoring ----------

function factor(key, label, points, max, value, strength, weakness, suggestion) {
  const r = points / max;
  return {
    key,
    label,
    points: Math.round(points * 10) / 10,
    max,
    value,
    status: r >= 0.8 ? 'good' : r >= 0.5 ? 'fair' : 'weak',
    strength,
    weakness,
    suggestion,
  };
}

const pct = (v) => `${Math.round(v * 100)}%`;

export function scoreFeatures(f) {
  const factors = [];
  const minSide = Math.min(f.width, f.height);

  // Resolution (15)
  const resPts = minSide >= 1080 ? 15 : minSide >= 800 ? 12 : minSide >= 600 ? 9 : minSide >= 400 ? 5 : 2;
  factors.push(
    factor('resolution', 'Resolution', resPts, 15, `${f.width}×${f.height} px`,
      `high resolution (${f.width}×${f.height} px)`,
      `low resolution (shortest side ${minSide} px), which can look soft on modern screens`,
      'Export at least 1080 px on the shortest side (e.g. 1080×1080 or 1080×1350) so the creative stays crisp on high-density screens.')
  );

  // Format fit (10)
  const dev = f.formatDeviation;
  const fmtPts = dev <= 0.02 ? 10 : dev <= 0.06 ? 7 : dev <= 0.12 ? 4 : 2;
  factors.push(
    factor('format', 'Format fit', fmtPts, 10, `${f.ratioLabel} · nearest ${f.nearestFormat}`,
      `a standard placement ratio (${f.nearestFormat})`,
      `a non-standard aspect ratio (${f.ratioLabel}), so platforms may crop or letterbox it`,
      'Crop to a standard placement ratio: 1:1 or 4:5 for feeds, 9:16 for stories and reels. That way platforms do not crop or letterbox key content.')
  );

  // Brightness (15)
  const b = f.brightness;
  const bDist = b < 0.35 ? 0.35 - b : b > 0.72 ? b - 0.72 : 0;
  const brPts = 15 * clamp(1 - bDist / 0.3);
  const tooDark = b < 0.35;
  factors.push(
    factor('brightness', 'Brightness', brPts, 15, pct(b),
      `balanced brightness (${pct(b)})`,
      tooDark ? `a dark overall exposure (${pct(b)}), which tends to get lost in busy feeds` : `a very bright, washed-out exposure (${pct(b)})`,
      tooDark
        ? 'Lift the exposure or place the product on a lighter background so the creative stands out in dark-mode and light-mode feeds.'
        : 'Reduce overexposed or pure-white areas and add a darker accent so the creative does not blend into white app backgrounds.')
  );

  // Contrast (20)
  const c = f.contrast;
  let ctPts;
  if (c < 0.2) ctPts = 20 * clamp((c - 0.04) / 0.16);
  else if (c <= 0.36) ctPts = 20;
  else ctPts = Math.max(12, 20 - ((c - 0.36) / 0.12) * 8);
  factors.push(
    factor('contrast', 'Contrast', ctPts, 20, pct(c),
      `strong tonal contrast (${pct(c)})`,
      c < 0.2 ? `low contrast (${pct(c)}), so the subject and text may not separate from the background` : `extreme contrast (${pct(c)}), which can feel harsh`,
      c < 0.2
        ? 'Increase the contrast between the subject, headline and background. For example, use dark text on a light panel or a bold colour behind the product.'
        : 'Soften the harshest highlights and shadows so the details in the subject stay readable.')
  );

  // Colourfulness (15)
  const M = f.colourfulness;
  let colPts;
  if (M < 30) colPts = Math.max(3, 15 * clamp((M - 5) / 25));
  else if (M <= 95) colPts = 15;
  else colPts = Math.max(9, 15 - ((M - 95) / 40) * 6);
  factors.push(
    factor('colour', 'Colourfulness', colPts, 15, `${M.toFixed(1)} (saturation ${pct(f.saturation)})`,
      'an engaging, varied colour palette',
      M < 30 ? 'a muted, low-colour palette that can look flat when people scroll past' : 'many competing saturated colours',
      M < 30
        ? 'Introduce one bold accent colour, for example on the call-to-action button or product, to catch attention while people scroll.'
        : 'Limit the palette to one primary colour and one accent so the key message is not competing with other colours.')
  );

  // Clarity (15)
  const s = f.sharpness;
  const shPts = s >= 250 ? 15 : Math.max(1, 15 * clamp(Math.log10(s + 1) / Math.log10(251)));
  factors.push(
    factor('clarity', 'Clarity', shPts, 15, s.toFixed(0),
      'crisp detail and clear edges',
      'soft or blurry detail (low Laplacian variance)',
      'Use a sharper source image and avoid heavy compression or upscaling. Blurry creatives tend to look low-quality.')
  );

  // Visual balance (10)
  const e = f.edgeDensity;
  let balPts;
  if (e < 0.03) balPts = 10 * (0.4 + 0.6 * (e / 0.03));
  else if (e <= 0.16) balPts = 10;
  else balPts = Math.max(2, 10 - ((e - 0.16) / 0.14) * 8);
  factors.push(
    factor('balance', 'Visual balance', balPts, 10, `${pct(e)} edge density`,
      'a clean, uncluttered composition',
      e < 0.03 ? 'very little visual structure, so there may be no clear focal point' : 'a busy, cluttered layout with lots of competing detail',
      e < 0.03
        ? 'Add a clear focal element, such as a product shot, a short headline or a CTA, so the creative does not read as visually empty.'
        : 'Simplify the layout. Remove secondary elements and leave empty space around the main message so it reads at a glance.')
  );

  const score = Math.round(factors.reduce((t, x) => t + x.points, 0));
  const category = score >= LIKELY_THRESHOLD ? CATEGORY.LIKELY : CATEGORY.LESS;

  // Explanation: biggest strengths and the factors that lost the most points.
  const byRatio = [...factors].sort((a, b) => b.points / b.max - a.points / a.max);
  const strengths = byRatio.filter((x) => x.status === 'good').slice(0, 2);
  const weaknesses = [...factors]
    .filter((x) => x.status !== 'good')
    .sort((a, b) => b.max - b.points - (a.max - a.points))
    .slice(0, 2);
  let explanation = `Scored ${score}/100 (threshold ${LIKELY_THRESHOLD}). `;
  if (strengths.length) explanation += `Strengths: ${strengths.map((x) => x.strength).join(' and ')}. `;
  if (weaknesses.length) explanation += `Holding it back: ${weaknesses.map((x) => x.weakness).join('; ')}.`;
  else explanation += 'No measured visual factor is notably weak.';

  const suggestions = weaknesses.map((x) => x.suggestion);
  const thirdWeak = [...factors]
    .filter((x) => x.status !== 'good' && !weaknesses.includes(x))
    .sort((a, b) => b.max - b.points - (a.max - a.points))[0];
  if (thirdWeak) suggestions.push(thirdWeak.suggestion);
  if (f.textLikeCoverage > 0.3 && suggestions.length < 3) {
    suggestions.push('A large share of the image contains text-like fine detail. If much of it is copy, shorten it to a short headline and move the details into the ad caption.');
  }
  const fallbacks = [
    'Keep key text and logos inside the central safe zone, because placements such as stories overlay the top and bottom edges.',
    'A/B test this creative against a variant with a different headline or CTA colour to confirm performance with real campaign data.',
    'Make sure the brand or product is identifiable within the first second of viewing.',
  ];
  for (const fb of fallbacks) if (suggestions.length < 2) suggestions.push(fb);

  const limitations = [
    'This is a rule-based visual estimate, not a trained ML prediction. It does not guarantee real reach.',
    'The message, offer, audience, targeting, budget and platform algorithm are not evaluated.',
  ];
  if (f.analysedWidth !== f.width) limitations.push(`Pixel measurements were taken on a ${f.analysedWidth}×${f.analysedHeight} px downscaled copy for consistency.`);
  if (f.transparentShare > 0.01) limitations.push('Transparent areas were measured as if placed on a white background.');
  limitations.push('Text-like detail coverage is a heuristic and is not used in the score.');

  return { score, category, factors, explanation: explanation.trim(), suggestions: suggestions.slice(0, 3), limitations };
}
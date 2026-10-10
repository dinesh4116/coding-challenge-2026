/**
 * Safe mathematical division preventing NaN and Infinity
 */
export function safeDivide(numerator: number, denominator: number, fallback = 0): number {
  if (!denominator || denominator === 0 || isNaN(denominator) || isNaN(numerator)) {
    return fallback
  }
  const result = numerator / denominator
  return isFinite(result) ? result : fallback
}

/**
 * Precision = TP / (TP + FP)
 * Returns value between 0 and 1, or 0 if denominator is 0
 */
export function calculatePrecision(tp: number, fp: number): number {
  return safeDivide(tp, tp + fp, 0)
}

/**
 * Recall = TP / (TP + FN)
 * Returns value between 0 and 1, or 0 if denominator is 0
 */
export function calculateRecall(tp: number, fn: number): number {
  return safeDivide(tp, tp + fn, 0)
}

/**
 * F1 Score = 2 * (Precision * Recall) / (Precision + Recall)
 */
export function calculateF1Score(precision: number, recall: number): number {
  if (precision + recall === 0) return 0
  return safeDivide(2 * precision * recall, precision + recall, 0)
}

/**
 * False Positive Rate (FPR) = FP / (FP + TN)
 */
export function calculateFPR(fp: number, tn: number): number {
  return safeDivide(fp, fp + tn, 0)
}

/**
 * Calculates all confusion matrix metrics safely
 */
export function calculateMetricsFromMatrix(tp: number, fp: number, fn: number, tn: number) {
  const precision = calculatePrecision(tp, fp)
  const recall = calculateRecall(tp, fn)
  const f1 = calculateF1Score(precision, recall)
  const fpr = calculateFPR(fp, tn)
  const accuracy = safeDivide(tp + tn, tp + fp + fn + tn, 0)

  return {
    tp,
    fp,
    fn,
    tn,
    precision,
    recall,
    f1Score: f1,
    falsePositiveRate: fpr,
    accuracy,
    total: tp + fp + fn + tn,
  }
}

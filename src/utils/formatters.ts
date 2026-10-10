import { format, parseISO, isValid } from 'date-fns'

export function formatCurrency(amount: number): string {
  if (isNaN(amount)) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: amount >= 100 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatNumber(val: number): string {
  if (isNaN(val)) return '0'
  return new Intl.NumberFormat('en-US', {
    notation: val >= 1000000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(val)
}

export function formatPercent(val: number, decimals = 1): string {
  if (isNaN(val)) return '0%'
  return `${(val * 100).toFixed(decimals)}%`
}

export function formatDeviation(percentDeviation: number): string {
  if (isNaN(percentDeviation)) return '0.0%'
  const prefix = percentDeviation > 0 ? '+' : ''
  return `${prefix}${percentDeviation.toFixed(1)}%`
}

export function formatDate(dateStr: string, formatPattern = 'MMM d, yyyy'): string {
  if (!dateStr) return '-'
  try {
    const d = parseISO(dateStr)
    return isValid(d) ? format(d, formatPattern) : dateStr
  } catch {
    return dateStr
  }
}

export function formatDateTime(dateStr: string): string {
  return formatDate(dateStr, 'MMM d, yyyy HH:mm')
}

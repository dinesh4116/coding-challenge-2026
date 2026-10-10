import { Alert, AlertFilterOptions, AlertStatus } from '../types/alert'
import { ALERTS } from '../data/challengeDataset'
import { ApiClient, getApiConfig } from './apiClient'

const STORAGE_KEY_ALERTS = 'campaignguard_alerts_store'

function getStoredAlerts(): Alert[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_ALERTS)
    if (raw) {
      const parsed = JSON.parse(raw)
      // Check if stored alerts match current dataset length
      if (Array.isArray(parsed) && parsed.length === ALERTS.length) {
        return parsed
      }
    }
  } catch {
    // fallback
  }
  return [...ALERTS]
}

function saveStoredAlerts(alerts: Alert[]): void {
  try {
    localStorage.setItem(STORAGE_KEY_ALERTS, JSON.stringify(alerts))
  } catch {
    // ignore
  }
}

export class AlertService {
  static async getAlerts(filters?: AlertFilterOptions): Promise<Alert[]> {
    const config = getApiConfig()
    let alerts: Alert[] = []

    if (!config.useDemoData) {
      try {
        alerts = await ApiClient.get<Alert[]>('/api/alerts')
      } catch (err) {
        console.warn('Backend unavailable, using challenge alert data:', err)
        alerts = getStoredAlerts()
      }
    } else {
      alerts = getStoredAlerts()
    }

    // Filter by severity
    if (filters?.severity && filters.severity !== 'all') {
      alerts = alerts.filter((a) => a.severity === filters.severity)
    }

    // Filter by status
    if (filters?.status && filters.status !== 'all') {
      alerts = alerts.filter((a) => a.status === filters.status)
    }

    // Filter by category
    if (filters?.category && filters.category !== 'all') {
      alerts = alerts.filter((a) => a.category === filters.category)
    }

    // Filter by campaign
    if (filters?.campaignId && filters.campaignId !== 'all') {
      alerts = alerts.filter((a) => a.campaignId === filters.campaignId)
    }

    // Filter by metric
    if (filters?.metric && filters.metric !== 'all') {
      alerts = alerts.filter((a) => a.metric === filters.metric)
    }

    // Search query
    if (filters?.searchQuery) {
      const q = filters.searchQuery.toLowerCase()
      alerts = alerts.filter(
        (a) =>
          (a.title && a.title.toLowerCase().includes(q)) ||
          a.campaignName.toLowerCase().includes(q) ||
          a.id.toLowerCase().includes(q)
      )
    }

    // Sorting
    if (filters?.sortBy) {
      alerts.sort((a, b) => {
        if (filters.sortBy === 'newest') {
          return new Date(b.firstDetected).getTime() - new Date(a.firstDetected).getTime()
        }
        if (filters.sortBy === 'oldest') {
          return new Date(a.firstDetected).getTime() - new Date(b.firstDetected).getTime()
        }
        if (filters.sortBy === 'severity') {
          const rank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 }
          return (rank[b.severity] || 0) - (rank[a.severity] || 0)
        }
        if (filters.sortBy === 'deviation') {
          return Math.abs(b.relativeDeviation) - Math.abs(a.relativeDeviation)
        }
        return 0
      })
    } else {
      // Default: sort by newest
      alerts.sort(
        (a, b) => new Date(b.firstDetected).getTime() - new Date(a.firstDetected).getTime()
      )
    }

    return alerts
  }

  static async getAlertById(id: string): Promise<Alert | null> {
    const config = getApiConfig()
    if (!config.useDemoData) {
      try {
        return await ApiClient.get<Alert>(`/api/alerts/${id}`)
      } catch {
        // fallback
      }
    }
    const alerts = getStoredAlerts()
    return alerts.find((a) => a.id === id) || null
  }

  static async updateAlertStatus(id: string, newStatus: AlertStatus, actor = 'Analyst'): Promise<Alert | null> {
    const alerts = getStoredAlerts()
    const index = alerts.findIndex((a) => a.id === id)
    if (index === -1) return null

    const existingTimeline = alerts[index].timeline || []
    const updatedAlert: Alert = {
      ...alerts[index],
      status: newStatus,
      timeline: [
        {
          timestamp: new Date().toISOString(),
          event: `Status updated to ${newStatus.toUpperCase()}`,
          actor,
          type: 'status_change',
        },
        ...existingTimeline,
      ],
    }

    alerts[index] = updatedAlert
    saveStoredAlerts(alerts)
    return updatedAlert
  }

  static copyAlertSummary(alert: Alert): string {
    const text = `[CampaignGuard Alert ${alert.id}]
Campaign: ${alert.campaignName} (${alert.channel})
Severity: ${alert.severity.toUpperCase()} | Status: ${alert.status.toUpperCase()}
Metric: ${alert.metric.toUpperCase()} | Observed: ${alert.observedValue} (Expected: ${alert.expectedBaseline})
Deviation: ${alert.relativeDeviation > 0 ? '+' : ''}${alert.relativeDeviation.toFixed(1)}% | Anomaly Score: ${alert.anomalyScore} MAD
Classification: ${alert.category}
Explanation: ${alert.explanation.whatChanged}
Recommended Step: ${alert.explanation.recommendedFirstStep}`
    return text
  }
}

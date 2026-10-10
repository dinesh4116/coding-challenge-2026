import { Incident, IncidentStatus } from '../types/incident'
import { INCIDENTS } from '../data/challengeDataset'
import { ApiClient, getApiConfig } from './apiClient'

const STORAGE_KEY_INCIDENTS = 'campaignguard_incidents_store'

function getStoredIncidents(): Incident[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_INCIDENTS)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length === INCIDENTS.length) {
        return parsed
      }
    }
  } catch {
    // fallback
  }
  return [...INCIDENTS]
}

function saveStoredIncidents(incidents: Incident[]): void {
  try {
    localStorage.setItem(STORAGE_KEY_INCIDENTS, JSON.stringify(incidents))
  } catch {
    // ignore
  }
}

export class IncidentService {
  static async getIncidents(options?: {
    status?: string
    category?: string
    severity?: string
    search?: string
  }): Promise<Incident[]> {
    const config = getApiConfig()
    let incidents: Incident[] = []

    if (!config.useDemoData) {
      try {
        incidents = await ApiClient.get<Incident[]>('/api/incidents')
      } catch (err) {
        console.warn('Backend unavailable, using challenge incident data:', err)
        incidents = getStoredIncidents()
      }
    } else {
      incidents = getStoredIncidents()
    }

    if (options?.status && options.status !== 'all') {
      incidents = incidents.filter((i) => i.status === options.status)
    }

    if (options?.category && options.category !== 'all') {
      incidents = incidents.filter((i) => i.category === options.category)
    }

    if (options?.severity && options.severity !== 'all') {
      incidents = incidents.filter((i) => i.severity === options.severity)
    }

    if (options?.search) {
      const q = options.search.toLowerCase()
      incidents = incidents.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          i.campaignName.toLowerCase().includes(q) ||
          i.id.toLowerCase().includes(q)
      )
    }

    return incidents
  }

  static async getIncidentById(id: string): Promise<Incident | null> {
    const config = getApiConfig()
    if (!config.useDemoData) {
      try {
        return await ApiClient.get<Incident>(`/api/incidents/${id}`)
      } catch {
        // fallback
      }
    }
    const incidents = getStoredIncidents()
    return incidents.find((i) => i.id === id) || null
  }

  static async updateIncidentStatus(id: string, newStatus: IncidentStatus, actor = 'Analyst'): Promise<Incident | null> {
    const incidents = getStoredIncidents()
    const idx = incidents.findIndex((i) => i.id === id)
    if (idx === -1) return null

    const existingTimeline = incidents[idx].timeline || []
    const updated: Incident = {
      ...incidents[idx],
      status: newStatus,
      endDate: newStatus === 'resolved' ? new Date().toISOString().split('T')[0] : incidents[idx].endDate,
      timeline: [
        {
          date: new Date().toISOString().replace('T', ' ').substring(0, 16),
          note: `Incident status updated to ${newStatus.toUpperCase()}`,
          actor,
        },
        ...existingTimeline,
      ],
    }

    incidents[idx] = updated
    saveStoredIncidents(incidents)
    return updated
  }
}

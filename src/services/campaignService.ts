import { Campaign, MetricDataPoint } from '../types/campaign'
import { Alert } from '../types/alert'
import { CAMPAIGNS, CAMPAIGN_METRICS_MAP, ALERTS } from '../data/challengeDataset'
import { ApiClient, getApiConfig } from './apiClient'

export class CampaignService {
  static async getCampaigns(options?: {
    channel?: string
    status?: string
    search?: string
    sortBy?: 'name' | 'spend' | 'clicks' | 'conversions' | 'health'
    sortOrder?: 'asc' | 'desc'
  }): Promise<Campaign[]> {
    const config = getApiConfig()

    let campaigns: Campaign[] = []
    if (!config.useDemoData) {
      try {
        campaigns = await ApiClient.get<Campaign[]>('/api/campaigns')
      } catch (err) {
        console.warn('Backend unavailable, using challenge dataset:', err)
        campaigns = [...CAMPAIGNS]
      }
    } else {
      campaigns = [...CAMPAIGNS]
    }

    // Apply filtering
    if (options?.channel && options.channel !== 'all') {
      campaigns = campaigns.filter((c) => c.channel === options.channel)
    }
    if (options?.status && options.status !== 'all') {
      campaigns = campaigns.filter((c) => c.status === options.status)
    }
    if (options?.search) {
      const q = options.search.toLowerCase()
      campaigns = campaigns.filter(
        (c) => c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q)
      )
    }

    // Apply sorting
    if (options?.sortBy) {
      const order = options.sortOrder === 'desc' ? -1 : 1
      campaigns.sort((a, b) => {
        if (options.sortBy === 'name') return order * a.name.localeCompare(b.name)
        if (options.sortBy === 'spend') return order * (a.spendToday - b.spendToday)
        if (options.sortBy === 'clicks') return order * (a.clicksToday - b.clicksToday)
        if (options.sortBy === 'conversions') return order * (a.conversionsToday - b.conversionsToday)
        if (options.sortBy === 'health') return order * a.status.localeCompare(b.status)
        return 0
      })
    }

    return campaigns
  }

  static async getCampaignById(id: string): Promise<Campaign | null> {
    const config = getApiConfig()
    if (!config.useDemoData) {
      try {
        return await ApiClient.get<Campaign>(`/api/campaigns/${id}`)
      } catch {
        // fallback
      }
    }
    const found = CAMPAIGNS.find((c) => c.id === id)
    return found || null
  }

  static async getCampaignMetrics(
    campaignId: string,
    dateRange: '7d' | '30d' | '90d' | '180d' = '180d'
  ): Promise<MetricDataPoint[]> {
    const points = CAMPAIGN_METRICS_MAP[campaignId] || []
    let daysToInclude = 180
    if (dateRange === '7d') daysToInclude = 7
    else if (dateRange === '30d') daysToInclude = 30
    else if (dateRange === '90d') daysToInclude = 90

    return points.slice(-daysToInclude)
  }

  static async getCampaignAlerts(campaignId: string): Promise<Alert[]> {
    return ALERTS.filter((a) => a.campaignId === campaignId)
  }
}

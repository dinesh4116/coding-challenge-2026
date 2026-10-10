export interface ApiConfig {
  baseUrl: string
  useDemoData: boolean
}

const STORAGE_KEY_API_CONFIG = 'campaignguard_api_config'

export const defaultApiConfig: ApiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  useDemoData: true, // Default to synthetic demo data unless backend is explicitly connected
}

export function getApiConfig(): ApiConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_API_CONFIG)
    if (stored) return { ...defaultApiConfig, ...JSON.parse(stored) }
  } catch {
    // ignore json error
  }
  return defaultApiConfig
}

export function saveApiConfig(config: Partial<ApiConfig>): ApiConfig {
  const current = getApiConfig()
  const updated = { ...current, ...config }
  localStorage.setItem(STORAGE_KEY_API_CONFIG, JSON.stringify(updated))
  return updated
}

export class ApiClient {
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const config = getApiConfig()
    const url = `${config.baseUrl}${endpoint}`

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    const response = await fetch(url, { ...options, headers })
    if (!response.ok) {
      const errorBody = await response.text()
      throw new Error(`API Error ${response.status}: ${errorBody || response.statusText}`)
    }
    return response.json()
  }

  static async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  static async post<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  static async patch<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  static async checkHealth(): Promise<{ status: string; version?: string }> {
    try {
      const config = getApiConfig()
      const response = await fetch(`${config.baseUrl}/api/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      })
      if (response.ok) {
        return await response.json()
      }
      return { status: 'disconnected' }
    } catch {
      return { status: 'disconnected' }
    }
  }
}

import { User, LoginCredentials } from './types'

const STORAGE_KEY_USER = 'campaignguard_auth_user'
const STORAGE_KEY_REMEMBER = 'campaignguard_auth_remember'

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase() || 'CG'
}

export class AuthService {
  /**
   * Retrieves currently persisted user session from storage
   */
  static getCurrentUser(): User | null {
    try {
      if (typeof window === 'undefined') return null

      // Check session storage first (current browser session)
      if (typeof sessionStorage !== 'undefined') {
        const sessionRaw = sessionStorage.getItem(STORAGE_KEY_USER)
        if (sessionRaw) {
          return JSON.parse(sessionRaw)
        }
      }

      // If "remember me" was checked, check local storage
      if (typeof localStorage !== 'undefined') {
        const localRaw = localStorage.getItem(STORAGE_KEY_USER)
        if (localRaw) {
          return JSON.parse(localRaw)
        }
      }
    } catch (e) {
      console.warn('Failed to parse stored user session:', e)
    }
    return null
  }

  /**
   * Authenticate using explicit credentials (Mode B - Demo / Hackathon environment)
   * Note: Passwords are NEVER persisted in client-side storage.
   */
  static async loginWithCredentials(
    credentials: LoginCredentials
  ): Promise<{ success: boolean; error?: string; user?: User }> {
    // Artificial latency for authentic feeling async validation
    await new Promise((resolve) => setTimeout(resolve, 450))

    const email = credentials.email?.trim() || ''
    const password = credentials.password || ''

    if (!email) {
      return { success: false, error: 'Email address is required.' }
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      return { success: false, error: 'Please enter a valid email address.' }
    }

    if (!password) {
      return { success: false, error: 'Password is required.' }
    }

    if (password.length < 6) {
      return { success: false, error: 'Password must be at least 6 characters long.' }
    }

    const usernamePart = email.split('@')[0]
    const cleanName = usernamePart
      .replace(/[._-]/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase())

    const user: User = {
      id: `usr-${Date.now()}`,
      email,
      name: cleanName || 'Ad Ops Analyst',
      role: 'Campaign Operations Analyst',
      avatarInitials: getInitials(cleanName || email),
      isDemoUser: false,
      lastLogin: new Date().toISOString(),
    }

    this.persistUser(user, !!credentials.rememberMe)

    return { success: true, user }
  }

  /**
   * Authenticate via one-click Demo Access for PS-04 Evaluators
   */
  static async loginDemo(): Promise<User> {
    // Brief processing animation
    await new Promise((resolve) => setTimeout(resolve, 300))

    const demoUser: User = {
      id: 'usr-demo-evaluator',
      email: 'evaluator@hackathon.demo',
      name: 'Hackathon Evaluator',
      role: 'Lead Anomaly Analyst (Demo Access)',
      avatarInitials: 'HE',
      isDemoUser: true,
      lastLogin: new Date().toISOString(),
    }

    // Persist in session storage for demo evaluation
    this.persistUser(demoUser, true)

    return demoUser
  }

  /**
   * Terminate active user session
   */
  static logout(): void {
    try {
      if (typeof window !== 'undefined') {
        if (typeof sessionStorage !== 'undefined') {
          sessionStorage.removeItem(STORAGE_KEY_USER)
        }
        if (typeof localStorage !== 'undefined') {
          localStorage.removeItem(STORAGE_KEY_USER)
          localStorage.removeItem(STORAGE_KEY_REMEMBER)
        }
      }
    } catch (e) {
      console.warn('Error clearing auth storage:', e)
    }
  }

  /**
   * Persist user session safely without sensitive credentials
   */
  private static persistUser(user: User, rememberMe: boolean): void {
    try {
      if (typeof window === 'undefined') return

      const serialized = JSON.stringify(user)
      if (typeof sessionStorage !== 'undefined') {
        sessionStorage.setItem(STORAGE_KEY_USER, serialized)
      }

      if (typeof localStorage !== 'undefined') {
        if (rememberMe) {
          localStorage.setItem(STORAGE_KEY_USER, serialized)
          localStorage.setItem(STORAGE_KEY_REMEMBER, 'true')
        } else {
          localStorage.removeItem(STORAGE_KEY_USER)
          localStorage.removeItem(STORAGE_KEY_REMEMBER)
        }
      }
    } catch (e) {
      console.warn('Failed to persist user session:', e)
    }
  }
}

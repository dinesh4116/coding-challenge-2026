import { describe, it, expect, beforeEach } from 'vitest'
import { AuthService } from '../../auth/authService'

// In-memory Storage mock for Node / Vitest test environment
class MockStorage implements Storage {
  private store: Map<string, string> = new Map()

  get length(): number {
    return this.store.size
  }

  clear(): void {
    this.store.clear()
  }

  getItem(key: string): string | null {
    return this.store.get(key) ?? null
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null
  }

  removeItem(key: string): void {
    this.store.delete(key)
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value))
  }
}

// Attach mocks to global context
const mockSessionStorage = new MockStorage()
const mockLocalStorage = new MockStorage()

// @ts-ignore
globalThis.window = globalThis
// @ts-ignore
globalThis.sessionStorage = mockSessionStorage
// @ts-ignore
globalThis.localStorage = mockLocalStorage

describe('AuthService — PS-04 Authentication & Demo Access', () => {
  beforeEach(() => {
    mockSessionStorage.clear()
    mockLocalStorage.clear()
  })

  it('loginDemo creates a valid evaluator session without credentials', async () => {
    const user = await AuthService.loginDemo()

    expect(user).toBeDefined()
    expect(user.isDemoUser).toBe(true)
    expect(user.name).toBe('Hackathon Evaluator')
    expect(user.role).toContain('Demo Access')
    expect(user.email).toBe('evaluator@hackathon.demo')
    expect(user.avatarInitials).toBe('HE')

    // Persisted in session storage
    const current = AuthService.getCurrentUser()
    expect(current).not.toBeNull()
    expect(current?.id).toBe(user.id)
  })

  it('loginWithCredentials rejects empty email', async () => {
    const result = await AuthService.loginWithCredentials({
      email: '',
      password: 'Password123!',
    })

    expect(result.success).toBe(false)
    expect(result.error).toContain('Email address is required')
  })

  it('loginWithCredentials rejects malformed email address', async () => {
    const result = await AuthService.loginWithCredentials({
      email: 'not-an-email',
      password: 'Password123!',
    })

    expect(result.success).toBe(false)
    expect(result.error).toContain('valid email address')
  })

  it('loginWithCredentials rejects empty password', async () => {
    const result = await AuthService.loginWithCredentials({
      email: 'analyst@adtech.co',
      password: '',
    })

    expect(result.success).toBe(false)
    expect(result.error).toContain('Password is required')
  })

  it('loginWithCredentials rejects short password (< 6 chars)', async () => {
    const result = await AuthService.loginWithCredentials({
      email: 'analyst@adtech.co',
      password: '123',
    })

    expect(result.success).toBe(false)
    expect(result.error).toContain('at least 6 characters')
  })

  it('loginWithCredentials succeeds with valid credentials and derives display name', async () => {
    const result = await AuthService.loginWithCredentials({
      email: 'marcus.vance@agency.com',
      password: 'SecurePassword2026!',
      rememberMe: true,
    })

    expect(result.success).toBe(true)
    expect(result.user).toBeDefined()
    expect(result.user?.email).toBe('marcus.vance@agency.com')
    expect(result.user?.name).toBe('Marcus Vance')
    expect(result.user?.isDemoUser).toBe(false)

    // Verify localStorage has user profile but NEVER password
    const stored = mockLocalStorage.getItem('campaignguard_auth_user')
    expect(stored).not.toBeNull()
    const parsed = JSON.parse(stored!)
    expect(parsed.email).toBe('marcus.vance@agency.com')
    expect(parsed.password).toBeUndefined()
    expect(mockLocalStorage.getItem('password')).toBeNull()
    expect(mockSessionStorage.getItem('password')).toBeNull()
  })

  it('logout terminates active session and clears both storages', async () => {
    await AuthService.loginDemo()
    expect(AuthService.getCurrentUser()).not.toBeNull()

    AuthService.logout()
    expect(AuthService.getCurrentUser()).toBeNull()
    expect(mockSessionStorage.getItem('campaignguard_auth_user')).toBeNull()
    expect(mockLocalStorage.getItem('campaignguard_auth_user')).toBeNull()
  })

  it('respects rememberMe false by storing only in sessionStorage', async () => {
    await AuthService.loginWithCredentials({
      email: 'session.only@agency.com',
      password: 'ValidPassword123!',
      rememberMe: false,
    })

    expect(mockSessionStorage.getItem('campaignguard_auth_user')).not.toBeNull()
    expect(mockLocalStorage.getItem('campaignguard_auth_user')).toBeNull()
  })
})

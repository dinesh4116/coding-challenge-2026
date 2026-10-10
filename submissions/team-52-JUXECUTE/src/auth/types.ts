export interface User {
  id: string
  email: string
  name: string
  role: string
  avatarInitials: string
  isDemoUser: boolean
  lastLogin: string
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  isDemoMode: boolean
}

export interface LoginCredentials {
  email: string
  password?: string
  rememberMe?: boolean
}

export interface AuthContextType extends AuthState {
  loginWithCredentials: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string }>
  loginDemo: () => Promise<void>
  logout: () => void
}

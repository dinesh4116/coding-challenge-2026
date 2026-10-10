import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, AuthContextType, LoginCredentials } from './types'
import { AuthService } from './authService'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    // Check for existing session on initial load
    try {
      const existingUser = AuthService.getCurrentUser()
      if (existingUser) {
        setUser(existingUser)
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const loginWithCredentials = async (
    credentials: LoginCredentials
  ): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true)
    try {
      const result = await AuthService.loginWithCredentials(credentials)
      if (result.success && result.user) {
        setUser(result.user)
        return { success: true }
      }
      return { success: false, error: result.error || 'Authentication failed' }
    } finally {
      setIsLoading(false)
    }
  }

  const loginDemo = async (): Promise<void> => {
    setIsLoading(true)
    try {
      const demoUser = await AuthService.loginDemo()
      setUser(demoUser)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    AuthService.logout()
    setUser(null)
  }

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    isDemoMode: user?.isDemoUser ?? true,
    loginWithCredentials,
    loginDemo,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

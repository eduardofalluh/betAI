import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getStoredToken, setStoredToken } from '../lib/api'
import { authMe, login as apiLogin, signup as apiSignup } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = getStoredToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const data = await authMe()
      setUser(data?.user ?? null)
    } catch {
      setStoredToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password)
    setStoredToken(data.token)
    setUser(data.user ?? null)
    return data
  }, [])

  const signup = useCallback(async (email, password) => {
    const data = await apiSignup(email, password)
    setStoredToken(data.token)
    setUser(data.user ?? null)
    return data
  }, [])

  const logout = useCallback(() => {
    setStoredToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser: loadUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

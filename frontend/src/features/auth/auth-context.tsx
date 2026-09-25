import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

import {
  getCurrentUser,
  login as loginRequest,
  revokeCurrentSession,
  verifyMfa,
  type MFAChallenge,
  type Token,
  type User,
} from './api'
import {
  clearSession,
  hasRefreshToken,
  refreshSession,
  sessionExpiredEvent,
  setSession,
} from './session'

type AuthContextValue = {
  user: User | null
  challenge: MFAChallenge | null
  isInitializing: boolean
  login: (
    username: string,
    password: string,
  ) => Promise<'authenticated' | 'mfa'>
  verifyChallenge: (code: string) => Promise<void>
  logout: () => Promise<void>
  clearLocalSession: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null)
  const [challenge, setChallenge] = useState<MFAChallenge | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)

  const acceptTokens = useCallback(async (tokens: Token) => {
    setSession(tokens)
    try {
      setUser(await getCurrentUser())
    } catch (error) {
      clearSession()
      throw error
    }
  }, [])

  useEffect(() => {
    let active = true
    async function restore() {
      if (!hasRefreshToken() || !(await refreshSession())) return
      try {
        const currentUser = await getCurrentUser()
        if (active) setUser(currentUser)
      } catch {
        clearSession()
      }
    }

    void restore().finally(() => {
      if (active) setIsInitializing(false)
    })

    const expire = () => {
      clearSession()
      setUser(null)
    }
    globalThis.addEventListener?.(sessionExpiredEvent, expire)
    return () => {
      active = false
      globalThis.removeEventListener?.(sessionExpiredEvent, expire)
    }
  }, [])

  const login = useCallback(
    async (username: string, password: string) => {
      const result = await loginRequest(username, password)
      if ('mfa_required' in result) {
        setChallenge(result)
        return 'mfa' as const
      }
      await acceptTokens(result)
      return 'authenticated' as const
    },
    [acceptTokens],
  )

  const verifyChallenge = useCallback(
    async (code: string) => {
      if (!challenge) throw new Error('登录验证已过期，请重新登录。')
      await acceptTokens(await verifyMfa(challenge.challenge_token, code))
      setChallenge(null)
    },
    [acceptTokens, challenge],
  )

  const logout = useCallback(async () => {
    try {
      await revokeCurrentSession()
    } finally {
      clearSession()
      setUser(null)
      setChallenge(null)
    }
  }, [])

  const clearLocalSession = useCallback(() => {
    clearSession()
    setUser(null)
    setChallenge(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      challenge,
      isInitializing,
      login,
      verifyChallenge,
      logout,
      clearLocalSession,
    }),
    [
      user,
      challenge,
      isInitializing,
      login,
      verifyChallenge,
      logout,
      clearLocalSession,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Provider and hook form one public authentication boundary.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

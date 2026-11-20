import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import {
  AuthenticatedUser,
  loginUser,
  logoutUser,
  getCurrentUser,
} from '../api/auth';
import { setOnUnauthorized, setAuthToken } from '../api/client';

interface AuthContextValue {
  user: AuthenticatedUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  clearSessionExpired: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Register unauthorized listener to catch expired sessions across any API call
  useEffect(() => {
    setOnUnauthorized(() => {
      setUser(null);
      setAuthToken(null);
      setSessionExpired(true);
    });

    return () => {
      setOnUnauthorized(null);
    };
  }, []);

  // Silent session re-hydration using HttpOnly cookie on application load
  useEffect(() => {
    let mounted = true;

    async function checkExistingSession() {
      try {
        const currentUser = await getCurrentUser();
        if (mounted && currentUser) {
          setUser(currentUser);
        }
      } catch {
        // If unauthenticated or cookie missing/expired, keep user null
        if (mounted) {
          setUser(null);
          setAuthToken(null);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    checkExistingSession();

    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setSessionExpired(false);
    try {
      const response = await loginUser(email, password);
      setUser(response.user);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed. Please try again.';
      setError(message);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch {
      // Proceed even if network request fails
    } finally {
      setUser(null);
      setAuthToken(null);
      setSessionExpired(false);
      setError(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);
  const clearSessionExpired = useCallback(() => setSessionExpired(false), []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        error,
        sessionExpired,
        login,
        logout,
        clearError,
        clearSessionExpired,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

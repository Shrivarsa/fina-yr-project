import { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { supabase } from './lib/supabase';
import { User as SupabaseUser, Session } from '@supabase/supabase-js';

interface User {
  user_id: string;
  email: string;
  username: string;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();

        if (session) {
          await setUserFromSession(session);
        } else {
          const stored = localStorage.getItem('scip_auth');
          if (stored) {
            try {
              const auth = JSON.parse(stored);
              if (auth.accessToken) {
                const { data: { user: supabaseUser } } = await supabase.auth.getUser(auth.accessToken);
                if (supabaseUser) {
                  setUser(auth.user);
                  setAccessToken(auth.accessToken);
                } else {
                  localStorage.removeItem('scip_auth');
                }
              }
            } catch (e) {
              localStorage.removeItem('scip_auth');
            }
          }
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        await setUserFromSession(session);
      } else if (event === 'SIGNED_OUT') {
        setUser(null);
        setAccessToken(null);
        localStorage.removeItem('scip_auth');
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const setUserFromSession = async (session: Session) => {
    if (!session.user) return;

    try {
      // Try to fetch existing profile
      const { data: profile, error } = await supabase
        .from('users')
        .select('username, email')
        .eq('id', session.user.id)
        .single();

      if (error && error.code === 'PGRST116') {
        // Profile doesn't exist yet — create it now (handles email confirmation flow)
        const username =
          session.user.user_metadata?.username ||
          session.user.email?.split('@')[0] ||
          'user';

        const { error: insertError } = await supabase
          .from('users')
          .insert({
            id: session.user.id,
            email: session.user.email,
            username,
          });

        if (insertError) {
          console.error('Error creating user profile on first login:', insertError);
        }

        const userData: User = {
          user_id: session.user.id,
          email: session.user.email || '',
          username,
        };

        setUser(userData);
        setAccessToken(session.access_token);
        localStorage.setItem(
          'scip_auth',
          JSON.stringify({ user: userData, accessToken: session.access_token })
        );
        return;
      }

      if (error) {
        console.error('Error fetching user profile:', error);
      }

      const userData: User = {
        user_id: session.user.id,
        email: session.user.email || '',
        username: profile?.username || session.user.email?.split('@')[0] || 'user',
      };

      setUser(userData);
      setAccessToken(session.access_token);
      localStorage.setItem(
        'scip_auth',
        JSON.stringify({ user: userData, accessToken: session.access_token })
      );
    } catch (error) {
      console.error('Error setting user from session:', error);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        throw new Error(error.message || 'Login failed');
      }

      if (data.session) {
        await setUserFromSession(data.session);
      } else {
        throw new Error('No session returned from login');
      }
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, username: string) => {
    setIsLoading(true);
    try {
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { username }, // store username in auth metadata for use after email confirmation
        },
      });

      if (authError) {
        throw new Error(authError.message || 'Registration failed');
      }

      if (!authData.user) {
        throw new Error('Failed to create user account');
      }

      if (authData.session) {
        // Email confirmation is disabled — session is available immediately
        // Insert profile now while we have an authenticated session
        const { error: profileError } = await supabase
          .from('users')
          .insert({
            id: authData.user.id,
            email: email,
            username: username,
          });

        if (profileError) {
          console.error('Error creating user profile:', profileError);
          throw new Error(`Failed to create user profile: ${profileError.message}`);
        }

        await setUserFromSession(authData.session);
      } else {
        // Email confirmation is required — profile will be created automatically
        // on first login via setUserFromSession (see PGRST116 handler above)
        throw new Error('Please check your email to confirm your account before logging in.');
      }
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (error) {
      console.error('Error during logout:', error);
    }
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem('scip_auth');
  };

  return (
    <AuthContext.Provider value={{ user, accessToken, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
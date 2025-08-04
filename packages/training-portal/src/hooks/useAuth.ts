import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '@/types/training';
import { api } from '@/services/api';
import { useRouter } from 'next/navigation';
import { toast } from 'react-hot-toast';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          const { token, user } = await api.login(email, password);
          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
          });
          toast.success(`歡迎回來，${user.name}！`);
        } catch (error) {
          set({ isLoading: false });
          toast.error('登入失敗，請檢查您的帳號密碼');
          throw error;
        }
      },

      logout: async () => {
        try {
          await api.logout();
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
          });
          toast.success('您已成功登出');
        }
      },

      checkAuth: async () => {
        const token = localStorage.getItem('training_token');
        if (!token) {
          set({ isAuthenticated: false, user: null, token: null });
          return;
        }

        try {
          const profile = await api.getProfile();
          set({
            user: profile.user,
            isAuthenticated: true,
            token,
          });
        } catch (error) {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
          });
          localStorage.removeItem('training_token');
        }
      },
    }),
    {
      name: 'training-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Hook for protected routes
export const useRequireAuth = () => {
  const router = useRouter();
  const { isAuthenticated, checkAuth } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      checkAuth().then(() => {
        if (!isAuthenticated) {
          router.push('/login');
        }
      });
    }
  }, [isAuthenticated, checkAuth, router]);

  return isAuthenticated;
};

// Hook for role-based access
export const useRequireRole = (requiredRoles: string[]) => {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated && user && !requiredRoles.includes(user.role)) {
      toast.error('您沒有權限訪問此頁面');
      router.push('/dashboard');
    }
  }, [user, isAuthenticated, requiredRoles, router]);

  return user && requiredRoles.includes(user.role);
};

import { useEffect } from 'react';
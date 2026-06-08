'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, usePlanningStore } from '@/lib/store';
import { LogOut, MapPin } from 'lucide-react';
import { authLogout } from '@/lib/backend-api';

export function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, user, logout } = useAuthStore();
  const { resetAll } = usePlanningStore();

  const handleLogout = async () => {
    await authLogout().catch(() => undefined);
    resetAll();
    logout();
    router.push('/auth');
  };

  return (
    <div className="min-h-screen bg-background paper-texture">
      {/* Top Bar */}
      <header className="sticky top-0 z-50 bg-white/95 border-b border-primary/10 backdrop-blur-sm shadow-sm">
        <div className="flex items-center justify-between px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            {/* Logo with travel theme */}
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-md">
                <MapPin className="w-5 h-5 text-white" />
              </div>
              {/* Small accent */}
              <div className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-accent border border-white shadow-sm" />
            </div>

            <div className="hidden sm:block">
              <div className="text-sm font-bold text-slate-800">AI旅行规划</div>
              <div className="text-xs text-muted-foreground">路线 · 车票 · 地图</div>
            </div>
          </div>

          {/* Decorative line */}
          <div className="hidden md:block flex-1 h-px bg-gradient-to-r from-primary/0 via-primary/20 to-primary/0 mx-4" />

          <div className="flex items-center gap-3">
            {isAuthenticated && user && (
              <>
                <div className="text-right hidden xs:block">
                  <div className="text-xs font-medium text-slate-700">{user}</div>
                  <div className="text-[10px] text-muted-foreground">已登录</div>
                </div>
                <div className="w-px h-6 bg-border" />
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-primary bg-slate-100/50 hover:bg-primary/10 px-3 py-1.5 rounded-lg transition-all duration-200 border border-slate-200/50 hover:border-primary/30"
                >
                  <LogOut className="w-3 h-3" />
                  <span className="hidden sm:inline">退出</span>
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        {children}
      </main>

      {/* Footer accent */}
      <div className="fixed bottom-0 left-0 right-0 h-px bg-gradient-to-r from-primary/0 via-primary/20 to-primary/0 pointer-events-none" />
    </div>
  );
}

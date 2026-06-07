'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';

export function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push('/auth');
  };

  return (
    <div className="min-h-screen bg-slate-50/30">
      {/* Top Bar */}
      <header className="sticky top-0 z-50 bg-white border-b border-slate-200/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-4 py-2 md:px-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-teal-500 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0L4.344 14.657a4 4 0 010-5.656l4.688-4.688a4 4 0 015.656 0L17.657 8a4 4 0 010 5.657z" />
              </svg>
            </div>
            <span className="font-semibold text-slate-800 hidden sm:inline">AI旅行规划工作台</span>
          </div>

          <div className="flex items-center gap-3">
            {isAuthenticated && user && (
              <>
                <span className="text-sm text-slate-600">账号: {user}</span>
                <button
                  onClick={handleLogout}
                  className="text-xs text-slate-500 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-md transition-colors"
                >
                  退出
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}

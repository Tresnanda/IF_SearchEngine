'use client';

import { signOut, useSession } from 'next-auth/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Database, LogOut } from 'lucide-react';
import { useEffect } from 'react';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/login');
    }
  }, [router, status]);

  if (status === 'loading') {
    return <div className="flex min-h-screen items-center justify-center text-zinc-500">Checking session...</div>;
  }

  if (status === 'unauthenticated') {
    return <div className="flex min-h-screen items-center justify-center text-zinc-500">Redirecting to login...</div>;
  }

  return (
    <div className="flex min-h-screen bg-zinc-50">
      <aside className="hidden w-64 flex-col border-r border-zinc-200 bg-white md:flex">
        <div className="border-b border-zinc-200 p-6">
          <h2 className="font-semibold text-zinc-900">Admin Portal</h2>
          <p className="mt-1 truncate text-xs text-zinc-500">{session?.user?.email}</p>
        </div>

        <nav className="flex-1 space-y-1 p-4">
          <Link
            href="/admin"
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${pathname === '/admin' ? 'bg-zinc-100 text-zinc-900' : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'}`}
          >
            <Database className="h-4 w-4" />
            Repository
          </Link>
        </nav>

        <div className="border-t border-zinc-200 p-4">
          <button
            onClick={() => signOut({ callbackUrl: '/' })}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm font-medium text-zinc-600 transition-colors hover:bg-red-50 hover:text-red-600"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

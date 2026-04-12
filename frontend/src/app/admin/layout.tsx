'use client';

import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Database, LayoutDashboard } from "lucide-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const pathname = usePathname();

  if (status === "loading") return <div className="min-h-screen flex items-center justify-center text-zinc-500">Loading...</div>;

  return (
    <div className="min-h-screen bg-zinc-50 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-200 bg-white flex flex-col hidden md:flex">
        <div className="p-6 border-b border-zinc-200">
          <h2 className="font-semibold text-zinc-900">Admin Portal</h2>
          <p className="text-xs text-zinc-500 truncate mt-1">{session?.user?.email}</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <Link href="/admin" className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${pathname === '/admin' ? 'bg-zinc-100 text-zinc-900' : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'}`}>
            <Database className="w-4 h-4" />
            Repository
          </Link>
        </nav>
        <div className="p-4 border-t border-zinc-200">
          <button onClick={() => signOut({ callbackUrl: '/' })} className="flex items-center gap-3 px-3 py-2 w-full text-left rounded-md text-sm font-medium text-zinc-600 hover:bg-red-50 hover:text-red-600 transition-colors">
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
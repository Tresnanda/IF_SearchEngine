'use client';

import { useState } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    const res = await signIn('credentials', {
      redirect: false,
      email,
      password,
    });

    if (res?.error) {
      setError('Invalid credentials');
    } else {
      router.push('/admin');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4">
      <div className="w-full max-w-md bg-white border border-zinc-200 rounded-xl shadow-sm p-8">
        <h1 className="text-2xl font-semibold text-zinc-900 mb-2">Admin Login</h1>
        <p className="text-zinc-500 text-sm mb-6">Sign in with your university credentials to manage the repository.</p>
        
        {error && <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md border border-red-100">{error}</div>}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Email</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-950 focus:border-zinc-950" 
              placeholder="admin@informatika.unud.ac.id"
              required 
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-950 focus:border-zinc-950" 
              placeholder="password"
              required 
            />
          </div>
          <button 
            type="submit" 
            className="w-full py-2 px-4 bg-zinc-950 hover:bg-zinc-800 text-white text-sm font-medium rounded-md transition-colors mt-2"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
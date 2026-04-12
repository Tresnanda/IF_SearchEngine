'use client';

import { useState, useEffect } from 'react';
import { Trash2, RefreshCw, Upload, FileText } from 'lucide-react';

const ADMIN_TOKEN = "super-secret-admin-token-123";

interface Thesis {
  id: number;
  title: string;
  filename: string;
  upload_date: string;
  is_indexed: boolean;
}

export default function RepositoryPage() {
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);

  const fetchTheses = async () => {
    try {
      const res = await fetch('/api/admin/repository', {
        headers: { 'X-Admin-Token': ADMIN_TOKEN } // Next.js rewrites this to :5000
      });
      if (res.ok) setTheses(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTheses();
  }, []);

  const handleIndex = async () => {
    if (!confirm('This will parse all documents and rebuild the search index. This may take several minutes. Continue?')) return;
    setIndexing(true);
    try {
      const res = await fetch('/api/admin/index', {
        method: 'POST',
        headers: { 'X-Admin-Token': ADMIN_TOKEN }
      });
      if (res.ok) {
        alert('Index rebuilt successfully!');
        fetchTheses();
      } else {
        alert('Failed to rebuild index.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIndexing(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      const res = await fetch(`/api/admin/delete/${id}`, {
        method: 'DELETE',
        headers: { 'X-Admin-Token': ADMIN_TOKEN }
      });
      if (res.ok) fetchTheses();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div className="p-8 text-zinc-500">Loading repository data...</div>;

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Thesis Repository</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage documents in the search engine index.</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={handleIndex}
            disabled={indexing}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-zinc-200 text-zinc-700 text-sm font-medium rounded-md hover:bg-zinc-50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${indexing ? 'animate-spin' : ''}`} />
            {indexing ? 'Rebuilding Index...' : 'Rebuild Search Index'}
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-zinc-950 text-white text-sm font-medium rounded-md hover:bg-zinc-800 transition-colors">
            <Upload className="w-4 h-4" />
            Upload Document
          </button>
        </div>
      </div>

      <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-medium">
            <tr>
              <th className="px-6 py-3">Document</th>
              <th className="px-6 py-3">Upload Date</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {theses.map(t => (
              <tr key={t.id} className="hover:bg-zinc-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-zinc-400" />
                    <div>
                      <p className="font-medium text-zinc-900 line-clamp-1">{t.title}</p>
                      <p className="text-xs text-zinc-500">{t.filename}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {new Date(t.upload_date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${t.is_indexed ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                    {t.is_indexed ? 'Indexed' : 'Pending Reindex'}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button onClick={() => handleDelete(t.id)} className="text-zinc-400 hover:text-red-600 transition-colors p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {theses.length === 0 && (
              <tr><td colSpan={4} className="px-6 py-8 text-center text-zinc-500">No documents found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
'use client';

import { useCallback, useEffect, useState } from 'react';
import { Trash2, RefreshCw, Upload, FileText } from 'lucide-react';

import ReindexStatusBadge from '@/components/admin/ReindexStatusBadge';
import UploadDialog from '@/components/admin/UploadDialog';

type ReindexStatus = 'idle' | 'running' | 'succeeded' | 'failed';

interface Thesis {
  id: number;
  title: string;
  filename: string;
  upload_date: string;
  is_indexed: boolean;
}

interface ReindexStatusResponse {
  status: ReindexStatus;
  last_error?: string | null;
}

export default function RepositoryPage() {
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<ReindexStatusResponse>({ status: 'idle' });

  const isReindexRunning = status.status === 'running';

  const fetchTheses = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/repository', { cache: 'no-store' });
      if (!res.ok) {
        setError('Failed to load repository.');
        return;
      }

      setTheses(await res.json());
      setError(null);
    } catch {
      setError('Failed to load repository.');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchReindexStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/reindex/status', { cache: 'no-store' });
      if (!res.ok) {
        return;
      }

      const payload = (await res.json()) as ReindexStatusResponse;
      setStatus({ status: payload.status, last_error: payload.last_error ?? null });
    } catch {
      return;
    }
  }, []);

  useEffect(() => {
    fetchTheses();
    fetchReindexStatus();

    const timer = window.setInterval(fetchReindexStatus, 3000);
    return () => window.clearInterval(timer);
  }, [fetchTheses, fetchReindexStatus]);

  const handleIndex = async () => {
    if (isReindexRunning || indexing) return;
    if (!confirm('This will parse all documents and rebuild the search index. This may take several minutes. Continue?')) return;

    setIndexing(true);
    try {
      const res = await fetch('/api/admin/reindex', {
        method: 'POST',
      });

      if (!res.ok) {
        setError('Failed to start reindex.');
      } else {
        setError(null);
      }

      await fetchReindexStatus();
    } catch {
      setError('Failed to start reindex.');
    } finally {
      setIndexing(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (isReindexRunning) return;
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      const res = await fetch(`/api/admin/delete/${id}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        setError('Failed to delete document.');
        return;
      }

      await fetchTheses();
      setError(null);
    } catch {
      setError('Failed to delete document.');
    }
  };

  const handleUploaded = async () => {
    await fetchTheses();
    await fetchReindexStatus();
  };

  if (loading) return <div className="p-8 text-zinc-500">Loading repository data...</div>;

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Thesis Repository</h1>
          <p className="mt-1 text-sm text-zinc-500">Manage documents in the search engine index.</p>
          <div className="mt-3">
            <ReindexStatusBadge status={status.status} lastError={status.last_error} />
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleIndex}
            disabled={indexing || isReindexRunning}
            className="flex items-center gap-2 rounded-md border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${indexing || isReindexRunning ? 'animate-spin' : ''}`} />
            {indexing || isReindexRunning ? 'Reindex Running...' : 'Rebuild Search Index'}
          </button>
          <button
            onClick={() => setUploadOpen(true)}
            disabled={isReindexRunning}
            className="flex items-center gap-2 rounded-md bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
          >
            <Upload className="h-4 w-4" />
            Upload Document
          </button>
        </div>
      </div>

      {error ? <p className="mb-4 text-sm text-zinc-700">{error}</p> : null}

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-200 bg-zinc-50 font-medium text-zinc-500">
            <tr>
              <th className="px-6 py-3">Document</th>
              <th className="px-6 py-3">Upload Date</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {theses.map((thesis) => (
              <tr key={thesis.id} className="hover:bg-zinc-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-zinc-400" />
                    <div>
                      <p className="line-clamp-1 font-medium text-zinc-900">{thesis.title}</p>
                      <p className="text-xs text-zinc-500">{thesis.filename}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-zinc-500">{new Date(thesis.upload_date).toLocaleDateString()}</td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${thesis.is_indexed ? 'border-zinc-300 bg-zinc-100 text-zinc-800' : 'border-zinc-200 bg-zinc-50 text-zinc-600'}`}
                  >
                    {thesis.is_indexed ? 'Indexed' : 'Pending Reindex'}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => handleDelete(thesis.id)}
                    disabled={isReindexRunning}
                    className="p-1 text-zinc-400 transition-colors hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
            {theses.length === 0 && (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-zinc-500">
                  No documents found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={handleUploaded}
        disabled={isReindexRunning}
      />
    </div>
  );
}

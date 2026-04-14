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
  source_type?: 'local' | 'gdrive';
  source_url?: string | null;
}

interface ReindexStatusResponse {
  status: ReindexStatus;
  last_error?: string | null;
  mode?: string | null;
  actor?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  active_version?: string | null;
  last_doc_count?: number | null;
  stats?: {
    created?: number;
    updated?: number;
    reused?: number;
    deleted?: number;
  } | null;
}

interface GdriveCreateResponse {
  error?: string;
}

export default function RepositoryPage() {
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [gdriveUrl, setGdriveUrl] = useState('');
  const [gdriveTitle, setGdriveTitle] = useState('');
  const [addingGdrive, setAddingGdrive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<ReindexStatusResponse>({ status: 'idle' });

  const isReindexRunning = status.status === 'running';

  const totals = {
    all: theses.length,
    indexed: theses.filter((thesis) => thesis.is_indexed).length,
    local: theses.filter((thesis) => thesis.source_type !== 'gdrive').length,
    gdrive: theses.filter((thesis) => thesis.source_type === 'gdrive').length,
  };
  const indexedPercent = totals.all > 0 ? Math.round((totals.indexed / totals.all) * 100) : 0;

  const domainMap = theses.reduce<Record<string, number>>((acc, thesis) => {
    const label = detectDomain(thesis.title);
    acc[label] = (acc[label] ?? 0) + 1;
    return acc;
  }, {});
  const domainBuckets = Object.entries(domainMap).sort((a, b) => b[1] - a[1]);

  const yearMap = theses.reduce<Record<string, number>>((acc, thesis) => {
    const year = parseYearFromTitle(thesis.title);
    if (!year) return acc;
    acc[year] = (acc[year] ?? 0) + 1;
    return acc;
  }, {});
  const yearBuckets = Object.entries(yearMap).sort((a, b) => Number(b[0]) - Number(a[0]));

  const reindexDurationLabel = formatReindexDuration(status.started_at, status.finished_at, status.status);

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

  const handleAddGdriveSource = async () => {
    if (!gdriveUrl.trim() || isReindexRunning || addingGdrive) return;

    setAddingGdrive(true);
    try {
      const response = await fetch('/api/admin/source/gdrive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: gdriveUrl.trim(), title: gdriveTitle.trim() || undefined }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as GdriveCreateResponse | null;
        setError(payload?.error ?? 'Failed to add Google Drive source.');
        return;
      }

      setGdriveUrl('');
      setGdriveTitle('');
      setError(null);
      await fetchTheses();
    } catch {
      setError('Failed to add Google Drive source.');
    } finally {
      setAddingGdrive(false);
    }
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
            {status.mode ? (
              <p className="mt-2 text-xs text-zinc-500 uppercase tracking-wide">Mode: {status.mode}</p>
            ) : null}
            {status.stats ? (
              <p className="mt-1 text-xs text-zinc-500">
                created {status.stats.created ?? 0}, updated {status.stats.updated ?? 0}, reused {status.stats.reused ?? 0}, deleted {status.stats.deleted ?? 0}
              </p>
            ) : null}
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

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Total Documents" value={`${totals.all}`} hint={`${totals.local} local • ${totals.gdrive} gdrive`} />
        <KpiCard label="Indexed Coverage" value={`${indexedPercent}%`} hint={`${totals.indexed}/${totals.all || 0} indexed`} />
        <KpiCard label="Active Index Version" value={status.active_version ?? 'n/a'} hint={`docs ${status.last_doc_count ?? 0}`} />
        <KpiCard label="Last Reindex Duration" value={reindexDurationLabel} hint={status.mode ? `mode ${status.mode}` : 'mode n/a'} />
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-700">Reindex Timeline</h2>
          <div className="mt-3 grid gap-3 text-sm text-zinc-600 sm:grid-cols-2">
            <TimelineItem label="Status" value={status.status} />
            <TimelineItem label="Actor" value={status.actor ?? '-'} />
            <TimelineItem label="Started" value={formatTimestamp(status.started_at)} />
            <TimelineItem label="Finished" value={formatTimestamp(status.finished_at)} />
          </div>
          {status.stats ? (
            <p className="mt-3 text-xs text-zinc-500">
              created {status.stats.created ?? 0}, updated {status.stats.updated ?? 0}, reused {status.stats.reused ?? 0}, deleted {status.stats.deleted ?? 0}
            </p>
          ) : null}
          {status.last_error ? <p className="mt-2 text-xs text-zinc-700">Error: {status.last_error}</p> : null}
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-700">Domain Distribution</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {domainBuckets.length > 0 ? (
              domainBuckets.map(([domain, count]) => (
                <span key={domain} className="inline-flex items-center rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs text-zinc-700">
                  {domain} {count}
                </span>
              ))
            ) : (
              <span className="text-xs text-zinc-500">No domain data</span>
            )}
          </div>
          <h3 className="mt-5 text-sm font-semibold uppercase tracking-wide text-zinc-700">Year Distribution</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {yearBuckets.length > 0 ? (
              yearBuckets.map(([year, count]) => (
                <span key={year} className="inline-flex items-center rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs text-zinc-700">
                  {year} {count}
                </span>
              ))
            ) : (
              <span className="text-xs text-zinc-500">No year data</span>
            )}
          </div>
        </div>
      </div>

      {error ? <p className="mb-4 text-sm text-zinc-700">{error}</p> : null}

      <div className="mb-5 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-700">Add from Google Drive</h2>
        <p className="mt-1 text-xs text-zinc-500">Use public-share link for MVP. File is indexed locally, users open source on Drive.</p>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_240px_auto]">
          <input
            type="url"
            placeholder="https://drive.google.com/file/d/.../view"
            value={gdriveUrl}
            onChange={(event) => setGdriveUrl(event.target.value)}
            disabled={isReindexRunning || addingGdrive}
            className="rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700"
          />
          <input
            type="text"
            placeholder="Optional title"
            value={gdriveTitle}
            onChange={(event) => setGdriveTitle(event.target.value)}
            disabled={isReindexRunning || addingGdrive}
            className="rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700"
          />
          <button
            type="button"
            onClick={handleAddGdriveSource}
            disabled={!gdriveUrl.trim() || isReindexRunning || addingGdrive}
            className="cursor-pointer rounded-md bg-zinc-950 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {addingGdrive ? 'Adding...' : 'Add Link'}
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-200 bg-zinc-50 font-medium text-zinc-500">
            <tr>
              <th className="px-6 py-3">Document</th>
              <th className="px-6 py-3">Source</th>
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
                <td className="px-6 py-4 text-xs text-zinc-500">
                  {thesis.source_type === 'gdrive' ? (
                    <a
                      href={thesis.source_url ?? '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="cursor-pointer text-blue-600 hover:text-blue-700"
                    >
                      Google Drive
                    </a>
                  ) : (
                    'Local Upload'
                  )}
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {thesis.upload_date ? new Date(thesis.upload_date).toLocaleDateString() : '-'}
                </td>
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
                <td colSpan={5} className="px-6 py-8 text-center text-zinc-500">
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

function KpiCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-zinc-900">{value}</p>
      <p className="mt-1 text-xs text-zinc-500">{hint}</p>
    </div>
  );
}

function TimelineItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-sm text-zinc-800">{value}</p>
    </div>
  );
}

function formatTimestamp(value?: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function formatReindexDuration(startedAt?: string | null, finishedAt?: string | null, status?: ReindexStatus): string {
  if (!startedAt) return 'n/a';

  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return 'n/a';

  const totalSeconds = Math.round((end - start) / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const base = `${minutes}m ${seconds}s`;
  return status === 'running' ? `${base} (running)` : base;
}

function parseYearFromTitle(title: string): string | null {
  const match = title.match(/\b(19|20)\d{2}\b/);
  return match ? match[0] : null;
}

function detectDomain(title: string): string {
  const lowered = title.toLowerCase();
  const domainRules: Array<{ label: string; keywords: string[] }> = [
    { label: 'sentiment', keywords: ['sentimen', 'sentiment', 'review', 'opini'] },
    { label: 'security', keywords: ['enkripsi', 'kriptografi', 'rsa', 'aes', 'cipher', 'keamanan'] },
    { label: 'computer vision', keywords: ['cnn', 'resnet', 'inception', 'gambar', 'vision'] },
    { label: 'nlp', keywords: ['text mining', 'ontology', 'token', 'bahasa'] },
    { label: 'recommender', keywords: ['rekomendasi', 'collaborative', 'slope one'] },
  ];

  for (const rule of domainRules) {
    if (rule.keywords.some((keyword) => lowered.includes(keyword))) {
      return rule.label;
    }
  }
  return 'other';
}

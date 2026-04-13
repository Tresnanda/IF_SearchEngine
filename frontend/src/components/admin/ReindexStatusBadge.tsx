type ReindexStatus = "idle" | "running" | "succeeded" | "failed";

type ReindexStatusBadgeProps = {
  status: ReindexStatus;
  lastError?: string | null;
};

const stylesByStatus: Record<ReindexStatus, string> = {
  idle: "border-zinc-200 bg-zinc-50 text-zinc-600",
  running: "border-zinc-300 bg-zinc-100 text-zinc-800",
  succeeded: "border-zinc-300 bg-zinc-100 text-zinc-800",
  failed: "border-zinc-300 bg-zinc-100 text-zinc-900",
};

const labelByStatus: Record<ReindexStatus, string> = {
  idle: "Idle",
  running: "Reindexing",
  succeeded: "Up to date",
  failed: "Reindex failed",
};

export default function ReindexStatusBadge({ status, lastError }: ReindexStatusBadgeProps) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${stylesByStatus[status]}`}
      >
        {labelByStatus[status]}
      </span>
      {status === "failed" && lastError ? (
        <span className="max-w-xs truncate text-xs text-zinc-500" title={lastError}>
          {lastError}
        </span>
      ) : null}
    </div>
  );
}

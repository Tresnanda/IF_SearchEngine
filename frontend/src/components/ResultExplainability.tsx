"use client";

import type { SearchResult } from "@/lib/api";
import { computeScoreBreakdown } from "@/lib/search-utils";

type ResultExplainabilityProps = {
  result: SearchResult;
};

export default function ResultExplainability({ result }: ResultExplainabilityProps) {
  const breakdown = computeScoreBreakdown(result);

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
      <span className="rounded border border-zinc-200 bg-zinc-50 px-2 py-1">
        title {breakdown.title_percent}%
      </span>
      <span className="rounded border border-zinc-200 bg-zinc-50 px-2 py-1">
        content {breakdown.content_percent}%
      </span>
      {result.year ? (
        <span className="rounded border border-zinc-200 bg-zinc-50 px-2 py-1">year {result.year}</span>
      ) : null}
      {result.domain ? (
        <span className="rounded border border-zinc-200 bg-zinc-50 px-2 py-1">domain {result.domain}</span>
      ) : null}
    </div>
  );
}

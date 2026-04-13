"use client";

type SearchFiltersProps = {
  years: string[];
  domains: string[];
  selectedYear: string;
  selectedDomain: string;
  onYearChange: (value: string) => void;
  onDomainChange: (value: string) => void;
};

export default function SearchFilters({
  years,
  domains,
  selectedYear,
  selectedDomain,
  onYearChange,
  onDomainChange,
}: SearchFiltersProps) {
  return (
    <div className="grid gap-3 border-b border-zinc-100 bg-white px-6 py-3 sm:grid-cols-2">
      <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
        Year
        <select
          className="rounded-md border border-zinc-200 bg-white px-2 py-2 text-sm text-zinc-700"
          value={selectedYear}
          onChange={(event) => onYearChange(event.target.value)}
        >
          <option value="all">All years</option>
          {years.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
        Domain
        <select
          className="rounded-md border border-zinc-200 bg-white px-2 py-2 text-sm text-zinc-700"
          value={selectedDomain}
          onChange={(event) => onDomainChange(event.target.value)}
        >
          <option value="all">All domains</option>
          {domains.map((domain) => (
            <option key={domain} value={domain}>
              {domain}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

'use client';

import { SearchResult } from '@/lib/api';
import { ExternalLink, Download } from 'lucide-react';
import SearchFeedback from './SearchFeedback';
import { useSearchParams } from 'next/navigation';
import SearchFilters from './SearchFilters';
import ResultExplainability from './ResultExplainability';
import { useMemo, useState } from 'react';

interface SearchResultsProps {
    results: SearchResult[];
}

export default function SearchResults({ results }: SearchResultsProps) {
    const searchParams = useSearchParams();
    const query = searchParams.get('q') || '';
    const [selectedYear, setSelectedYear] = useState('all');
    const [selectedDomain, setSelectedDomain] = useState('all');

    const years = useMemo(() => {
        const unique = new Set<string>();
        for (const result of results) {
            if (result.year) unique.add(result.year);
        }
        return Array.from(unique).sort((a, b) => b.localeCompare(a));
    }, [results]);

    const domains = useMemo(() => {
        const unique = new Set<string>();
        for (const result of results) {
            if (result.domain) unique.add(result.domain);
        }
        return Array.from(unique).sort();
    }, [results]);

    const filteredResults = useMemo(() => {
        return results.filter((result) => {
            const yearMatch = selectedYear === 'all' || result.year === selectedYear;
            const domainMatch = selectedDomain === 'all' || result.domain === selectedDomain;
            return yearMatch && domainMatch;
        });
    }, [results, selectedYear, selectedDomain]);

    if (results.length === 0) return null;

    return (
        <div className="w-full flex flex-col">
            <SearchFilters
                years={years}
                domains={domains}
                selectedYear={selectedYear}
                selectedDomain={selectedDomain}
                onYearChange={setSelectedYear}
                onDomainChange={setSelectedDomain}
            />
            {/* Header info */}
            <div className="px-6 py-3 border-b border-zinc-100 flex justify-between items-center bg-white text-xs font-medium text-zinc-500 uppercase tracking-wider">
                <span>Top Results</span>
                <span>{filteredResults.length} documents</span>
            </div>

            {/* Results List */}
            <div className="divide-y divide-zinc-100 bg-white">
                {filteredResults.map((result, index) => (
                    <div 
                        key={index}
                        className="p-6 hover:bg-zinc-50 transition-colors duration-150 group"
                    >
                        <div className="flex justify-between items-start gap-4">
                            
                            {/* Main Content */}
                            <div className="flex-1 min-w-0">
                                <h3 className="text-base font-semibold text-zinc-900 group-hover:text-blue-600 transition-colors leading-tight mb-1">
                                    {result.title}
                                </h3>
                                
                                <div className="flex items-center gap-3 text-xs text-zinc-500 mb-3">
                                    <span className="font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-100/50">
                                        BM25: {result.score.toFixed(3)}
                                    </span>
                                    <span className="truncate">{result.filename}</span>
                                </div>

                                {result.snippet && (
                                    <div className="text-sm text-zinc-600 leading-relaxed border-l-2 border-zinc-200 pl-3">
                                        <p className="line-clamp-3">{result.snippet}</p>
                                    </div>
                                )}

                                <ResultExplainability result={result} />
                            </div>

                            {/* Actions (Hidden until hover on desktop, always visible on mobile) */}
                            <div className="flex flex-col gap-2 shrink-0 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                                <a
                                    href={`/files/${result.filename}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center justify-center w-8 h-8 rounded text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 transition-colors"
                                    title="View Document"
                                >
                                    <ExternalLink className="w-4 h-4" />
                                </a>
                                <a
                                    href={`/files/${result.filename}`}
                                    download
                                    className="flex items-center justify-center w-8 h-8 rounded text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 transition-colors"
                                    title="Download Document"
                                >
                                    <Download className="w-4 h-4" />
                                </a>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Feedback Footer */}
            <div className="bg-zinc-50 border-t border-zinc-200 p-6">
                <SearchFeedback query={query} totalResults={filteredResults.length} />
            </div>
        </div>
    );
}

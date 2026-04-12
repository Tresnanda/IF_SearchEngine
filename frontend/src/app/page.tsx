'use client';

import { useState } from 'react';
import { Search } from 'lucide-react';
import { search, SearchResponse } from '@/lib/api';
import SearchResults from '@/components/SearchResults';

export default function Home() {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<SearchResponse | null>(null);

    const handleSearch = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        try {
            const res = await search(query);
            setData(res);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen bg-zinc-50 pt-20 px-4 sm:px-6 flex flex-col items-center">
            
            {/* Main Command Palette Container */}
            <div className="w-full max-w-3xl flex flex-col shadow-xl shadow-zinc-200/40 rounded-xl overflow-hidden border border-zinc-200 bg-white transition-all duration-300">
                
                {/* Search Input Area */}
                <form onSubmit={handleSearch} className="relative flex items-center border-b border-zinc-100 bg-white z-20">
                    <Search className="absolute left-4 w-5 h-5 text-zinc-400" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search academic corpus..."
                        className="w-full pl-12 pr-4 py-5 text-zinc-900 bg-transparent text-lg placeholder:text-zinc-400 focus:outline-none focus:ring-0"
                    />
                    <div className="absolute right-4 flex items-center gap-2">
                        {loading && (
                            <div className="w-4 h-4 border-2 border-zinc-300 border-t-blue-600 rounded-full animate-spin" />
                        )}
                        <button 
                            type="submit"
                            className="hidden sm:flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-zinc-500 bg-zinc-100 rounded-md hover:bg-zinc-200 transition-colors"
                        >
                            <kbd className="font-sans">↵</kbd>
                            Enter
                        </button>
                    </div>
                </form>

                {/* Results Area */}
                <div className="bg-zinc-50/50">
                    {data?.data && (
                        <SearchResults results={data.data} />
                    )}
                    {data?.data?.length === 0 && !loading && (
                        <div className="p-8 text-center text-zinc-500 text-sm">
                            No results found for "{query}".
                        </div>
                    )}
                </div>
            </div>

            {/* Optional Footer/Hint */}
            {!data && !loading && (
                <div className="mt-8 text-sm text-zinc-400 flex items-center gap-2">
                    <Search className="w-4 h-4" />
                    Information Retrieval Engine v2.0
                </div>
            )}
        </main>
    );
}
'use client';

import { SearchResult } from '@/lib/api';
import { motion } from 'framer-motion';
import { FileText, Download, Eye } from 'lucide-react';
// Import komponen baru
import SearchFeedback from './SearchFeedback'; 
// Asumsi kamu menambahkan prop 'query' dari parent juga untuk dikirim ke feedback
import { useSearchParams } from 'next/navigation';

interface SearchResultsProps {
    results: SearchResult[];
    // Kita butuh query asli untuk dikirim ke log feedback
    // Opsional: bisa pass query dari props, atau ambil dari URL param
}

export default function SearchResults({ results }: SearchResultsProps) {
    // Ambil query dari URL parameter untuk keperluan logging
    const searchParams = useSearchParams();
    const query = searchParams.get('q') || '';

    if (results.length === 0) return null;

    return (
        <div className="w-full max-w-5xl mx-auto space-y-6 pb-20">
            {/* Bagian Header Hasil Search (KODE LAMA TETAP SAMA) */}
            <div className="flex items-center justify-between px-2">
                <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
                    Search Results <span className="text-gray-400 font-normal">({results.length})</span>
                </h2>
            </div>

            {/* Grid Hasil Search (KODE LAMA TETAP SAMA) */}
            <div className="grid gap-6">
                {results.map((result, index) => (
                    <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: index * 0.1, ease: "easeOut" }}
                        className="group relative glass-card rounded-2xl p-6 hover:-translate-y-1 hover:shadow-2xl overflow-hidden"
                    >
                        {/* ... ISI KARTU TETAP SAMA SEPERTI FILE KAMU ... */}
                        
                        <div className="flex flex-col md:flex-row gap-6 relative z-10">
                             {/* ... Konten Icon ... */}
                             <div className="hidden md:flex flex-col items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800 shrink-0">
                                <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <h3 className="text-xl font-bold text-gray-900 dark:text-white leading-tight mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    {result.title}
                                </h3>
                                <div className="text-sm text-gray-500 mb-2">{result.filename}</div>
                                
                                {/* Score pills, dll tetap sama */}
                            </div>
                             
                             {/* Actions Buttons tetap sama */}
                             <div className="flex flex-row md:flex-col gap-2 shrink-0 pt-4 md:pt-0 justify-end md:justify-center">
                                {/* ... buttons ... */}
                             </div>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* --- TAMBAHKAN INI DI BAGIAN BAWAH --- */}
            <div className="pt-10 border-t border-gray-200 dark:border-gray-800 mt-10">
                <SearchFeedback query={query} totalResults={results.length} />
            </div>
        </div>
    );
}
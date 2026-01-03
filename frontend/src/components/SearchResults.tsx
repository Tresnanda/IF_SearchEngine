'use client';

import { SearchResult } from '@/lib/api';
import { motion } from 'framer-motion';
import { FileText, Download, Eye, ExternalLink } from 'lucide-react';

interface SearchResultsProps {
    results: SearchResult[];
}

export default function SearchResults({ results }: SearchResultsProps) {
    if (results.length === 0) return null;

    return (
        <div className="w-full max-w-5xl mx-auto space-y-6 pb-20">
            <div className="flex items-center justify-between px-2">
                <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
                    Search Results <span className="text-gray-400 font-normal">({results.length})</span>
                </h2>
            </div>

            <div className="grid gap-6">
                {results.map((result, index) => (
                    <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: index * 0.1, ease: "easeOut" }}
                        className="group relative glass-card rounded-2xl p-6 hover:-translate-y-1 hover:shadow-2xl overflow-hidden"
                    >
                        {/* Decorative gradient orb on hover */}
                        <div className="absolute -right-20 -top-20 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-all duration-500" />

                        <div className="flex flex-col md:flex-row gap-6 relative z-10">
                            {/* Icon / Thumbnail Area */}
                            <div className="hidden md:flex flex-col items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800 shrink-0">
                                <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-2 mb-3">
                                    <div className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 mr-2">
                                        <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                                    </div>
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800">
                                        Match Score: {(result.score * 100).toFixed(1)}%
                                    </span>
                                    <span className="text-xs text-gray-400 font-mono truncate max-w-[200px]" title={result.filename}>
                                        {result.filename}
                                    </span>
                                </div>

                                <h3 className="text-xl font-bold text-gray-900 dark:text-white leading-tight mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    {result.title}
                                </h3>

                                {/* Score Breakdown (Optional, can be hidden or shown on hover/expand) */}
                                <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 mt-4 pt-4 border-t border-gray-100 dark:border-gray-800/50">
                                    <div className="flex items-center gap-1">
                                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                                        Content: <span className="font-mono text-gray-700 dark:text-gray-300">{result.content_score.toFixed(4)}</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <div className="w-1.5 h-1.5 rounded-full bg-pink-500" />
                                        Title: <span className="font-mono text-gray-700 dark:text-gray-300">{result.title_score.toFixed(4)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="flex flex-row md:flex-col gap-2 shrink-0 pt-4 md:pt-0 border-t md:border-t-0 md:border-l border-gray-100 dark:border-gray-800 md:pl-6 justify-end md:justify-center">
                                <a
                                    href={`/files/${result.filename}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm font-medium hover:bg-blue-600 dark:hover:bg-blue-100 transition-colors shadow-lg shadow-gray-200 dark:shadow-none"
                                >
                                    <Eye className="w-4 h-4" />
                                    View PDF
                                </a>
                                <a
                                    href={`/files/${result.filename}`}
                                    download
                                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <Download className="w-4 h-4" />
                                    Save
                                </a>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}

'use client';

import { useState } from 'react';
import { submitFeedback } from '@/lib/api';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

interface SearchFeedbackProps {
    query: string;
    totalResults: number;
}

export default function SearchFeedback({ query, totalResults }: SearchFeedbackProps) {
    const [submitted, setSubmitted] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleFeedback = async (satisfied: boolean) => {
        setIsSubmitting(true);
        try {
            await submitFeedback({
                query,
                satisfied,
                relevant_count: satisfied ? Math.min(totalResults, 3) : 0,
                total_results: totalResults
            });
            setSubmitted(true);
        } catch (error) {
            console.error('Failed to submit feedback', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (submitted) {
        return (
            <div className="text-center text-sm text-zinc-500 py-2">
                Thank you for your feedback.
            </div>
        );
    }

    return (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <span className="text-sm text-zinc-600 font-medium">Are these results helpful?</span>
            <div className="flex gap-2">
                <button
                    onClick={() => handleFeedback(true)}
                    disabled={isSubmitting}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 hover:text-zinc-900 transition-colors disabled:opacity-50"
                >
                    <ThumbsUp className="w-4 h-4" />
                    Yes
                </button>
                <button
                    onClick={() => handleFeedback(false)}
                    disabled={isSubmitting}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 hover:text-zinc-900 transition-colors disabled:opacity-50"
                >
                    <ThumbsDown className="w-4 h-4" />
                    No
                </button>
            </div>
        </div>
    );
}
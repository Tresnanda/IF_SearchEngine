# Information Retrieval System UI/UX Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Next.js frontend to use a "Swiss Modernism / Notion" aesthetic and a centered "Command Palette" interaction flow.

**Architecture:** We will strip away existing heavy glassmorphism styles and replace them with strict Tailwind utility classes relying on the Zinc color scale. The main layout will be constrained to a single centered `max-w-3xl` container that holds both the search input and the expanding search results.

**Tech Stack:** Next.js (App Router), React, Tailwind CSS, Framer Motion, Lucide React.

---

### Task 1: Update Global Styles and Tailwind Config

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Update Tailwind Theme Variables**
Update the base theme in `globals.css` to ensure the background is slightly off-white and text colors are sharp.

```css
@import "tailwindcss";

@theme {
  --color-border: #e4e4e7; /* zinc-200 */
  --color-input: #f4f4f5; /* zinc-100 */
  --color-ring: #2563eb; /* blue-600 */
  --color-background: #fafafa; /* zinc-50 */
  --color-foreground: #09090b; /* zinc-950 */

  --color-primary: #09090b; /* zinc-950 */
  --color-primary-foreground: #fafafa; /* zinc-50 */

  --color-secondary: #f4f4f5; /* zinc-100 */
  --color-secondary-foreground: #18181b; /* zinc-900 */

  --color-muted: #f4f4f5; /* zinc-100 */
  --color-muted-foreground: #71717a; /* zinc-500 */
  
  --color-accent: #2563eb; /* blue-600 */
  --color-accent-foreground: #ffffff;

  --color-card: #ffffff;
  --color-card-foreground: #09090b;
}

body {
  background-color: var(--color-background);
  color: var(--color-foreground);
  font-family: system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* Remove old glassmorphism utility classes if they exist */
.glass-card {
  background: white;
  border: 1px solid var(--color-border);
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
```

- [ ] **Step 2: Commit**
```bash
cd frontend && git add src/app/globals.css
git commit -m "style: update global css for swiss modernism aesthetic"
```

---

### Task 2: Refactor Main Page Layout (Command Palette Style)

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Rewrite page.tsx layout**
Remove the old hero section, large background gradients, and sprawling layout. Create a single `max-w-3xl` container that houses the search bar and the `SearchResults` component.

```tsx
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
```

- [ ] **Step 2: Commit**
```bash
cd frontend && git add src/app/page.tsx
git commit -m "refactor: implement command palette layout in page.tsx"
```

---

### Task 3: Refactor Search Results Component

**Files:**
- Modify: `frontend/src/components/SearchResults.tsx`

- [ ] **Step 1: Rewrite SearchResults.tsx for strict minimalist look**
Remove `framer-motion` heavy animations, colored gradients, and large icons. Implement the Swiss Modernism grid for each result item.

```tsx
'use client';

import { SearchResult } from '@/lib/api';
import { ExternalLink, Download } from 'lucide-react';
import SearchFeedback from './SearchFeedback';
import { useSearchParams } from 'next/navigation';

interface SearchResultsProps {
    results: SearchResult[];
}

export default function SearchResults({ results }: SearchResultsProps) {
    const searchParams = useSearchParams();
    const query = searchParams.get('q') || '';

    if (results.length === 0) return null;

    return (
        <div className="w-full flex flex-col">
            {/* Header info */}
            <div className="px-6 py-3 border-b border-zinc-100 flex justify-between items-center bg-white text-xs font-medium text-zinc-500 uppercase tracking-wider">
                <span>Top Results</span>
                <span>{results.length} documents</span>
            </div>

            {/* Results List */}
            <div className="divide-y divide-zinc-100 bg-white">
                {results.map((result, index) => (
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
                <SearchFeedback query={query} totalResults={results.length} />
            </div>
        </div>
    );
}
```

- [ ] **Step 2: Commit**
```bash
cd frontend && git add src/components/SearchResults.tsx
git commit -m "refactor: apply minimal swiss aesthetic to search results"
```

---

### Task 4: Refactor Search Feedback Component

**Files:**
- Modify: `frontend/src/components/SearchFeedback.tsx`

- [ ] **Step 1: Simplify Feedback UI**
Ensure the feedback buttons fit the new minimal grayscale theme.

```tsx
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
```

- [ ] **Step 2: Commit**
```bash
cd frontend && git add src/components/SearchFeedback.tsx
git commit -m "refactor: apply minimal aesthetic to feedback component"
```

---

### Task 5: Build and Verify

- [ ] **Step 1: Run frontend build to verify compilation**
```bash
cd frontend && npm run build
```
*(If the build fails due to typescript errors, fix them inline and re-verify).*

- [ ] **Step 2: Final Commit**
```bash
git commit -am "chore: ensure frontend builds successfully after ui refactor"
```

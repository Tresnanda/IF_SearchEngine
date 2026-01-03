export interface SearchResult {
    title: string;
    filename: string;
    score: number;
    content_score: number;
    title_score: number;
}

export interface SearchResponse {
    status: string;
    correction: string | null;
    data: SearchResult[];
}

export async function search(query: string): Promise<SearchResponse> {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) {
        throw new Error('Search failed');
    }
    return res.json();
}

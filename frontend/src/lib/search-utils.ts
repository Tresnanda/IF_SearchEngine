import type { SearchResult } from "@/lib/api";

export type ScoreBreakdown = {
  title_percent: number;
  content_percent: number;
};

export function computeScoreBreakdown(result: SearchResult): ScoreBreakdown {
  const title = Math.max(0, result.title_score ?? 0);
  const content = Math.max(0, result.content_score ?? 0);
  const total = title + content;

  if (total <= 0) {
    return { title_percent: 0, content_percent: 0 };
  }

  return {
    title_percent: Math.round((title / total) * 100),
    content_percent: Math.round((content / total) * 100),
  };
}

export function parseYearFromTitle(title: string): string | null {
  const match = title.match(/\b(19|20)\d{2}\b/);
  return match ? match[0] : null;
}

export function detectDomain(title: string): string {
  const lower = title.toLowerCase();
  const domainRules: Array<{ label: string; keywords: string[] }> = [
    { label: "sentiment", keywords: ["sentimen", "sentiment", "opini", "review"] },
    { label: "security", keywords: ["enkripsi", "kriptografi", "rsa", "aes", "cipher", "keamanan"] },
    { label: "computer vision", keywords: ["cnn", "resnet", "inception", "gambar", "object detection", "vision"] },
    { label: "nlp", keywords: ["text mining", "stemming", "token", "bahasa", "ontology", "ontology"] },
    { label: "recommender", keywords: ["recommend", "rekomendasi", "collaborative", "slope one"] },
  ];

  for (const rule of domainRules) {
    if (rule.keywords.some((keyword) => lower.includes(keyword))) {
      return rule.label;
    }
  }

  return "other";
}

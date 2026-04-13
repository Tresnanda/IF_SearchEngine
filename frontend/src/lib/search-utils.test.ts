import { describe, expect, it } from "vitest";

import { computeScoreBreakdown, detectDomain, parseYearFromTitle } from "./search-utils";

describe("search-utils", () => {
  it("computes score contribution percentages", () => {
    const breakdown = computeScoreBreakdown({
      title: "x",
      filename: "x.pdf",
      score: 1.0,
      title_score: 0.8,
      content_score: 0.2,
      snippet: "",
    });

    expect(breakdown.title_percent).toBe(80);
    expect(breakdown.content_percent).toBe(20);
  });

  it("extracts year from title when present", () => {
    expect(parseYearFromTitle("Analisis Sentimen 2024 Twitter")).toBe("2024");
    expect(parseYearFromTitle("Tanpa Tahun")).toBeNull();
  });

  it("detects domain heuristically", () => {
    expect(detectDomain("Implementasi Algoritma RSA untuk Keamanan Data")).toBe("security");
    expect(detectDomain("Judul Umum Tanpa Kata Kunci")).toBe("other");
  });
});

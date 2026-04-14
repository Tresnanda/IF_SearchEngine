import { describe, expect, it, vi } from "vitest";

import { search } from "./api";

describe("search api path", () => {
  it("calls backend search endpoint through /api/search proxy path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "success", correction: null, data: [] }),
    });

    vi.stubGlobal("fetch", fetchMock);

    await search("sentiment analysis");

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url.startsWith("/api/search?")).toBe(true);
  });
});

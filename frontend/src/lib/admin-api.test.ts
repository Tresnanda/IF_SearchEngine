import { describe, expect, it, vi, afterEach } from "vitest";

import { proxyToBackendAdmin } from "./admin-api";

describe("proxyToBackendAdmin", () => {
  const originalNodeEnv = process.env.NODE_ENV;
  const originalAdminInternalToken = process.env.ADMIN_INTERNAL_TOKEN;

  afterEach(() => {
    vi.unstubAllGlobals();
    process.env.NODE_ENV = originalNodeEnv;
    if (typeof originalAdminInternalToken === "undefined") {
      delete process.env.ADMIN_INTERNAL_TOKEN;
    } else {
      process.env.ADMIN_INTERNAL_TOKEN = originalAdminInternalToken;
    }
  });

  it("adds internal token and actor headers", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await proxyToBackendAdmin({
      path: "/admin/repository",
      method: "GET",
      actorEmail: "admin@informatika.unud.ac.id",
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;

    expect(headers["X-Internal-Admin-Token"]).toBeDefined();
    expect(headers["X-Admin-Actor"]).toBe("admin@informatika.unud.ac.id");
  });

  it("throws in production when ADMIN_INTERNAL_TOKEN is missing", async () => {
    process.env.NODE_ENV = "production";
    delete process.env.ADMIN_INTERNAL_TOKEN;

    await expect(
      proxyToBackendAdmin({
        path: "/admin/repository",
        method: "GET",
        actorEmail: "admin@informatika.unud.ac.id",
      }),
    ).rejects.toThrow("ADMIN_INTERNAL_TOKEN must be set in production");
  });
});

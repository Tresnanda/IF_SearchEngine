export type AdminMethod = "GET" | "POST" | "DELETE";

export async function proxyToBackendAdmin(params: {
  path: string;
  method: AdminMethod;
  actorEmail: string;
  body?: BodyInit;
  contentType?: string;
}) {
  const baseUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:5000";
  const isProduction = process.env.NODE_ENV === "production";
  const internalToken = process.env.ADMIN_INTERNAL_TOKEN ?? (isProduction ? undefined : "dev-admin-token");

  if (!internalToken) {
    throw new Error("ADMIN_INTERNAL_TOKEN must be set in production");
  }

  const headers: Record<string, string> = {
    "X-Internal-Admin-Token": internalToken,
    "X-Admin-Actor": params.actorEmail,
  };

  if (params.contentType) {
    headers["Content-Type"] = params.contentType;
  }

  return fetch(`${baseUrl}${params.path}`, {
    method: params.method,
    headers,
    body: params.body,
    cache: "no-store",
  });
}

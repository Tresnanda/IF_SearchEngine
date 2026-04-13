import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { proxyToBackendAdmin } from "@/lib/admin-api";
import { authOptions } from "@/lib/auth";

export async function POST() {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  try {
    const upstream = await proxyToBackendAdmin({
      path: "/admin/reindex",
      method: "POST",
      actorEmail: session.user.email ?? "admin@informatika.unud.ac.id",
    });

    const body = await upstream.text();
    const contentType = upstream.headers.get("content-type") ?? "application/json";

    return new NextResponse(body, {
      status: upstream.status,
      headers: { "Content-Type": contentType },
    });
  } catch {
    return NextResponse.json({ error: "Admin upstream unavailable" }, { status: 503 });
  }
}

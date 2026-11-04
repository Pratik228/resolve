const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api(path, opts) {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

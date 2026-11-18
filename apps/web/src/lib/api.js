const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const API_BASE = BASE;

export async function api(path, opts) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...opts,
      headers: { "Content-Type": "application/json", ...(opts?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new Error("The Resolve API is not reachable right now. Try again in a minute.");
  }
  if (res.status === 429) throw new Error("Rate limited. Wait a minute, then try again.");
  if (!res.ok) throw new Error(`The API answered ${res.status} for ${path}.`);
  return res.json();
}

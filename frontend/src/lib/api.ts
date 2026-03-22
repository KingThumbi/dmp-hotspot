const BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

async function parseJsonSafe(res: Response) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function extractErrorMessage(payload: any, status: number) {
  return payload?.error || payload?.message || `Request failed (${status})`;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  let res: Response;

  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Could not reach the server.");
  }

  const payload = await parseJsonSafe(res);

  if (!res.ok) {
    throw new Error(extractErrorMessage(payload, res.status));
  }

  return payload as T;
}

export async function apiGetWithAuth<T>(path: string): Promise<T> {
  let res: Response;

  try {
    res = await fetch(`${BASE}${path}`, {
      method: "GET",
      credentials: "include",
    });
  } catch {
    throw new Error("Could not reach the server.");
  }

  const payload = await parseJsonSafe(res);

  if (!res.ok) {
    throw new Error(extractErrorMessage(payload, res.status));
  }

  return payload as T;
}

export async function apiPostWithAuth<T>(path: string, body: unknown): Promise<T> {
  let res: Response;

  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Could not reach the server.");
  }

  const payload = await parseJsonSafe(res);

  if (!res.ok) {
    throw new Error(extractErrorMessage(payload, res.status));
  }

  return payload as T;
}
const RAW_API_BASE = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");

function isLocalApiBase(value: string): boolean {
  try {
    const url = new URL(value);
    return ["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  } catch {
    return false;
  }
}

function apiBase(): string {
  if (!RAW_API_BASE) {
    return "";
  }

  if (import.meta.env.PROD && isLocalApiBase(RAW_API_BASE)) {
    console.warn(
      "Ignoring local VITE_API_BASE_URL in production build; using same-origin API paths.",
      { configuredBase: RAW_API_BASE }
    );
    return "";
  }

  return RAW_API_BASE;
}

function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase()}${normalizedPath}`;
}

// -----------------------------
// Helpers
// -----------------------------
async function parseJsonSafe(res: Response): Promise<any> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function extractErrorMessage(payload: any, status: number): string {
  return (
    payload?.error ||
    payload?.message ||
    `Request failed (${status})`
  );
}

// -----------------------------
// Core request function (DRY)
// -----------------------------
type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = false } = options;

  let res: Response;
  const url = apiUrl(path);

  try {
    res = await fetch(url, {
      method,
      credentials: auth ? "include" : "same-origin",
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    console.error("API request failed before receiving a response.", {
      url,
      method,
      error,
    });
    throw new Error("Could not reach the server.");
  }

  const payload = await parseJsonSafe(res);

  if (!res.ok) {
    throw new Error(extractErrorMessage(payload, res.status));
  }

  return payload as T;
}

// -----------------------------
// Public API helpers
// -----------------------------

// GET (no auth)
export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

// POST (no auth)
export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body });
}

// GET (with auth / cookies)
export function apiGetWithAuth<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET", auth: true });
}

// POST (with auth / cookies)
export function apiPostWithAuth<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body, auth: true });
}

// PUT / PATCH / DELETE (future-ready)
export function apiPutWithAuth<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PUT", body, auth: true });
}

export function apiPatchWithAuth<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body, auth: true });
}

export function apiDeleteWithAuth<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE", auth: true });
}

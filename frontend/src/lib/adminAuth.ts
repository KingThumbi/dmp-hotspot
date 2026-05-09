const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

export function currentAdminNextPath(): string {
  const path = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  return path.startsWith("/admin-ui") ? path : "/admin-ui/dashboard";
}

export function adminLoginUrl(nextPath: string = currentAdminNextPath()): string {
  const safeNext = nextPath.startsWith("/admin-ui") ? nextPath : "/admin-ui/dashboard";
  return `${API_BASE}/admin/login?next=${encodeURIComponent(safeNext)}`;
}

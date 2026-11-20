const API_BASE: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

let inMemoryToken: string | null = null;
let unauthorizedListener: (() => void) | null = null;

/** Set the in-memory access token (used as Authorization Bearer header). */
export function setAuthToken(token: string | null): void {
  inMemoryToken = token;
}

/** Get the current in-memory access token. */
export function getAuthToken(): string | null {
  return inMemoryToken;
}

/** Register a callback triggered when any request returns 401 Unauthorized. */
export function setOnUnauthorized(callback: (() => void) | null): void {
  unauthorizedListener = callback;
}

/** Extract the CSRF token from document.cookie for Double-Submit Cookie defense. */
function getCsrfTokenFromCookie(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[2]) : null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  const csrfToken = getCsrfTokenFromCookie();
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(inMemoryToken ? { Authorization: `Bearer ${inMemoryToken}` } : {}),
    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
    ...(init?.headers as Record<string, string> ?? {}),
  };

  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      credentials: 'include', // Ensure HttpOnly cookies are transmitted
      headers,
    });
  } catch {
    throw new Error(`Cannot reach the BizPulse backend at ${API_BASE}`);
  }

  if (res.status === 401) {
    if (unauthorizedListener && !path.includes('/api/auth/login')) {
      unauthorizedListener();
    }
  }

  if (res.status === 403) {
    let detail = 'Access forbidden: You do not have permission for this action.';
    try {
      const body: unknown = await res.json();
      if (typeof body === 'object' && body !== null && 'detail' in body) {
        detail = String((body as { detail: unknown }).detail);
      }
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body: unknown = await res.json();
      if (typeof body === 'object' && body !== null && 'detail' in body) {
        const d = (body as { detail: unknown }).detail;
        if (typeof d === 'string') detail = d;
        else if (Array.isArray(d)) detail = 'The request was not valid.';
      }
    } catch {
      /* non-JSON error body — keep status text */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

/** GET a JSON resource from the BizPulse backend. */
export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

/** POST a JSON body to the BizPulse backend. */
export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/** PATCH a JSON body to the BizPulse backend. */
export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

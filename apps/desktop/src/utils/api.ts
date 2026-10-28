export function getSessionToken(): string | undefined {
  return typeof window !== 'undefined' ? window.phenom?.getSessionToken() : undefined;
}

export function getAuthHeaders(): Record<string, string> {
  const token = getSessionToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch(endpoint: string, init?: RequestInit): Promise<Response> {
  const url = endpoint.startsWith('http') ? endpoint : `http://127.0.0.1:8000${endpoint}`;
  const headers = new Headers(init?.headers || {});
  const token = getSessionToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(url, { ...init, headers });
}

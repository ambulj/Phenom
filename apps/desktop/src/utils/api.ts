export function getSessionToken(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  const electronToken = window.phenom?.getSessionToken();
  if (electronToken) return electronToken;
  const urlToken = new URLSearchParams(window.location.search).get('token');
  if (urlToken) return urlToken;
  const storedToken = localStorage.getItem('phenom_session_token');
  return storedToken || undefined;
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

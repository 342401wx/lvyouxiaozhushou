type ApiOptions = RequestInit & {
  json?: unknown;
};

export type BackendEnvelope<T = unknown> = {
  success?: boolean;
  message?: string;
  data?: T;
  authenticated?: boolean;
  user?: { id?: string; username?: string } | null;
};

export class BackendApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = 'BackendApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<BackendEnvelope<T>> {
  const headers = new Headers(options.headers);

  if (options.json !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: 'include',
    body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
  });

  const payload = (await response.json().catch(() => ({}))) as BackendEnvelope<T>;

  if (!response.ok || payload.success === false) {
    throw new BackendApiError(payload.message || `Request failed: ${path}`, response.status, payload);
  }

  return payload;
}

export function getErrorMessage(error: unknown, fallback = '请求失败，请稍后重试') {
  if (error instanceof BackendApiError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}

export function authMe() {
  return apiFetch('/api/auth/me');
}

export function authLogin(username: string, password: string) {
  return apiFetch('/api/auth/login', {
    method: 'POST',
    json: { username, password },
  });
}

export function authRegister(username: string, password: string) {
  return apiFetch('/api/auth/register', {
    method: 'POST',
    json: { username, password },
  });
}

export function authLogout() {
  return apiFetch('/api/auth/logout', { method: 'POST' });
}

export function getMemories() {
  return apiFetch('/api/memory');
}

export function getMemory(id: string | number) {
  return apiFetch(`/api/memory/${encodeURIComponent(String(id))}`);
}

export function parseIntent(message: string) {
  return apiFetch<Record<string, unknown>>('/api/intent', {
    method: 'POST',
    json: { message, text: message },
  });
}

export function previewIntercity(payload: Record<string, unknown>) {
  return apiFetch<Record<string, unknown>>('/api/intercity-options', {
    method: 'POST',
    json: payload,
  });
}

export function createPlan(payload: Record<string, unknown>) {
  return apiFetch<Record<string, unknown>>('/api/plan', {
    method: 'POST',
    json: payload,
  });
}

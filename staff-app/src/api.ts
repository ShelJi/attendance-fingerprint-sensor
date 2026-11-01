export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

export function serverUrl(value: string) {
  const url = new URL(value.trim());
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new Error('Enter a server origin, for example https://attendance.example.com');
  }
  return url.origin;
}

export function query(values: Record<string, string | number>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value !== '') params.set(key, String(value)); });
  return params.size ? `?${params}` : '';
}

export class Api {
  csrf = '';
  // Undefined uses browser cookies; native clients restore this from SecureStore.
  sessionKey: string | null | undefined;
  onSessionChange?: (sessionKey: string | null) => Promise<void>;
  onUnauthorized?: () => void;
  origin: string;
  private transport: typeof fetch;
  constructor(origin: string, transport: typeof fetch = fetch.bind(globalThis)) { this.origin = origin; this.transport = transport; }

  async response(path: string, body?: unknown) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    let response: Response;
    try {
      response = await this.transport(`${this.origin}/api/mobile/${path.startsWith('auth/') ? path : 'me/' + path}`, {
        method: body === undefined ? 'GET' : 'POST', credentials: this.sessionKey === undefined ? 'include' : 'omit',
        signal: controller.signal,
        headers: { Accept: path.startsWith('report/pdf/') ? 'application/pdf' : 'application/json',
          ...(this.sessionKey === undefined ? {} : {
            'X-App-Client': 'native',
            Cookie: [this.sessionKey ? `sessionid=${this.sessionKey}` : '', this.csrf ? `csrftoken=${this.csrf}` : ''].filter(Boolean).join('; '),
          }),
          ...(body === undefined ? {} : { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrf, Referer: `${this.origin}/` }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch {
      throw new Error('Could not reach the server. Check its URL, network connection, and HTTPS certificate.');
    } finally { clearTimeout(timer); }
    if (!response.ok) {
      let message = `Request failed (${response.status}).`;
      const data = await response.json().catch(() => null);
      if (data?.error) message = data.error;
      else if (data?.errors) message = Object.entries(data.errors).map(([field, errors]) =>
        `${field}: ${(errors as { message: string }[]).map(item => item.message).join(' ')}`).join('\n');
      else if (response.status === 403) message = 'CSRF verification failed. Sign in again to refresh your session.';
      else if (response.status === 404) message = `Mobile API not found at ${this.origin}/api/mobile/${path.split('?')[0]}. Check EXPO_PUBLIC_API_URL in the project .env, rebuild the app, and deploy/restart the Django backend with the mobile API routes.`;
      if (response.status === 401 && path !== 'auth/login/') {
        if (this.sessionKey !== undefined) { this.sessionKey = null; await this.onSessionChange?.(null); }
        this.onUnauthorized?.();
      }
      throw new ApiError(message, response.status);
    }
    return response;
  }

  private async json<T>(path: string, body?: unknown): Promise<T> {
    const response = await this.response(path, body);
    let data;
    try { data = await response.json(); }
    catch {
      throw new ApiError(`The server returned an invalid JSON response for /api/mobile/${path.split('?')[0]}. Check EXPO_PUBLIC_API_URL in the project .env, rebuild the app, and deploy/restart the Django mobile API.`, response.status);
    }
    if (this.sessionKey !== undefined && path.startsWith('auth/') && 'session_key' in data) {
      this.sessionKey = data.session_key;
      await this.onSessionChange?.(data.session_key);
    }
    return data;
  }
  async get<T>(path: string): Promise<T> { return this.json<T>(path); }
  async post<T>(path: string, body: unknown): Promise<T> { return this.json<T>(path, body); }
  async session() {
    const data = await this.get<{ authenticated: boolean; username: string | null; csrf_token: string }>('auth/session/');
    this.csrf = data.csrf_token;
    return data;
  }
  async login(username: string, password: string) {
    await this.session();
    const data = await this.post<{ username: string; csrf_token: string }>('auth/login/', { username, password });
    if (this.sessionKey === null) throw new Error('Deploy the backend update for saved mobile login, then sign in again.');
    this.csrf = data.csrf_token;
    return data.username;
  }
  async requireStaff() { await this.get('profile/'); }
  async logout() { await this.post('auth/logout/', {}); this.csrf = ''; }
}

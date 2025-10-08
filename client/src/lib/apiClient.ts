"use client";

type Tokens = {
  access_token: string;
  refresh_token: string;
};

type RequestOptions = RequestInit & {
  skipAuth?: boolean; // do not attach Authorization header
  retry?: boolean; // internal flag to avoid infinite loops
};

const TOKENS_KEY = "auth_tokens";
const LOGIN_PATH = "/login"; // change if your login route differs

export class ApiClient {
  private baseUrl: string;
  private tokens: Tokens | null = null;
  private refreshing: Promise<void> | null = null;
  private listeners: Set<() => void> = new Set();

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    if (typeof window !== "undefined") {
      const raw = window.localStorage.getItem(TOKENS_KEY);
      if (raw) {
        try {
          this.tokens = JSON.parse(raw);
        } catch {
          this.tokens = null;
        }
      }
    }
  }

  // ---------- Auth helpers ----------
  public isAuthenticated(): boolean {
    return !!this.tokens?.access_token;
  }

  public getAccessToken(): string | null {
    return this.tokens?.access_token || null;
  }

  public setTokens(tokens: Tokens) {
    this.tokens = tokens;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
    }
    this.notifyAuthChange();
  }

  public clearTokens() {
    this.tokens = null;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(TOKENS_KEY);
    }
    this.notifyAuthChange();
  }

  public async login(email: string, password: string): Promise<void> {
    const res = await this.post("/api/login", { email, password }, { skipAuth: true });
    this.assertOk(res);
    const data = await res.json();
    this.setTokens(data as Tokens);
  }

  public async register(name: string, email: string, password: string): Promise<void> {
    const res = await this.post("/api/register", { name, email, password }, { skipAuth: true });
    this.assertOk(res);
    const data = await res.json();
    this.setTokens(data as Tokens);
  }

  public async loginWithGoogle(idToken: string): Promise<void> {
    const res = await this.post("/api/login_with_google", { idToken }, { skipAuth: true });
    this.assertOk(res);
    const data = await res.json();
    this.setTokens(data as Tokens);
  }

  public logout() {
    this.clearTokens();
    if (typeof window !== "undefined") {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `${LOGIN_PATH}?next=${next}`;
    }
  }

  public onAuthChange(cb: () => void) {
    this.listeners.add(cb);
  }
  public offAuthChange(cb: () => void) {
    this.listeners.delete(cb);
  }
  private notifyAuthChange() {
    for (const cb of this.listeners) {
      try { cb(); } catch {}
    }
  }

  private async refreshAccessToken(): Promise<void> {
    if (this.refreshing) return this.refreshing;
    if (!this.tokens?.refresh_token) throw new Error("No refresh token");

    this.refreshing = (async () => {
      try {
        const res = await fetch(`${this.baseUrl}/api/token/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.tokens!.refresh_token}`,
          },
          credentials: "include",
        });
        if (!res.ok) {
          throw new Error("Refresh failed");
        }
        const data = (await res.json()) as Tokens;
        this.setTokens(data);
      } finally {
        this.refreshing = null;
      }
    })();

    return this.refreshing;
  }

  // ---------- Core request with auto auth/refresh ----------
  public async request(path: string, options: RequestOptions = {}): Promise<Response> {
    const url = path.startsWith("http") ? path : `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> | undefined),
    };

    // Attach Authorization unless skipped
    if (!options.skipAuth && this.tokens?.access_token) {
      headers["Authorization"] = `Bearer ${this.tokens.access_token}`;
    }

    // Optionally include guest ID for guest flows
    const guestId = this.getGuestId();
    if (guestId && !headers["X-Guest-Id"]) {
      headers["X-Guest-Id"] = guestId;
    }

    const init: RequestInit = {
      ...options,
      headers,
    };

    const res = await fetch(url, init);
    if (res.status !== 401) return res;

    // 401 handling: try refresh once and retry the original request
    if (!options.retry && this.tokens?.refresh_token) {
      try {
        await this.refreshAccessToken();
        return await this.request(path, { ...options, retry: true });
      } catch {
        // fallthrough to logout
      }
    }

    // No refresh or refresh failed → redirect to login (avoid loop if already on login)
    if (typeof window !== "undefined") {
      const path = window.location.pathname;
      if (!path.startsWith(LOGIN_PATH)) {
        const next = encodeURIComponent(path + window.location.search);
        window.location.href = `${LOGIN_PATH}?next=${next}`;
      }
    }
    return res; // return the 401 for any callers that await it in SSR contexts
  }

  public get(path: string, options?: RequestOptions) {
    return this.request(path, { ...(options || {}), method: "GET" });
  }
  public delete(path: string, options?: RequestOptions) {
    return this.request(path, { ...(options || {}), method: "DELETE" });
  }
  public post<TBody = unknown>(path: string, body?: TBody, options?: RequestOptions) {
    return this.request(path, {
      ...(options || {}),
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
      headers: body instanceof FormData ? options?.headers : { ...(options?.headers || {}), "Content-Type": "application/json" },
    });
  }
  public put<TBody = unknown>(path: string, body?: TBody, options?: RequestOptions) {
    return this.request(path, {
      ...(options || {}),
      method: "PUT",
      body: JSON.stringify(body ?? {}),
    });
  }
  public patch<TBody = unknown>(path: string, body?: TBody, options?: RequestOptions) {
    return this.request(path, {
      ...(options || {}),
      method: "PATCH",
      body: JSON.stringify(body ?? {}),
    });
  }

  // ---------- Utilities ----------
  private assertOk(res: Response) {
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
  }

  private getGuestId(): string | null {
    if (typeof window === "undefined") return null;
    const key = "guest_id";
    let id = window.localStorage.getItem(key);
    if (!id) {
      try {
        id = crypto.randomUUID();
      } catch {
        id = Math.random().toString(36).slice(2);
      }
      window.localStorage.setItem(key, id);
      document.cookie = `${key}=${id}; path=/; max-age=${60 * 60 * 24 * 365}`;
    }
    return id;
  }
}

// Export a ready-to-use singleton
export const api = new ApiClient(process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001");

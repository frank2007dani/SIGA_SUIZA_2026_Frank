const normalizeBase = (value) => (value || '').trim().replace(/\/+$/, '');

const apiBase = normalizeBase(import.meta.env.VITE_API_URL);

if (import.meta.env.PROD && !/^https:\/\//.test(apiBase)) {
  throw new Error('VITE_API_URL debe ser la URL HTTPS absoluta del backend de Render.');
}

const configuredWs = normalizeBase(import.meta.env.VITE_WS_URL).replace(/\/ws$/, '');
const derivedWs = apiBase
  ? apiBase.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;

export const API_BASE = apiBase;
export const WS_BASE = configuredWs || derivedWs;

const SENSITIVE_KEYS = new Set(['password', 'token', 'access_token', 'refresh_token', 'authorization']);

const redact = (value) => {
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        SENSITIVE_KEYS.has(key.toLowerCase()) ? '[REDACTED]' : redact(item),
      ]),
    );
  }
  return value;
};

const safeUrl = (url) => url.split('?')[0];

const debugRequest = (payload) => {
  if (import.meta.env.DEV) console.debug('[SIGA API]', payload);
};

class SIGAApiClient {
  constructor() {
    this.baseURL = API_BASE;
    this.token = localStorage.getItem('token');
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const { timeoutMs, ...fetchOptions } = options;
    const controller = timeoutMs ? new AbortController() : null;
    const timeoutId = controller
      ? setTimeout(() => controller.abort(), timeoutMs)
      : null;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
      ...fetchOptions,
      ...(controller && !fetchOptions.signal ? { signal: controller.signal } : {}),
    };

    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`;
    }

    const method = (config.method || 'GET').toUpperCase();
    debugRequest({ url: safeUrl(url), method });

    try {
      const response = await fetch(url, config);

      if (response.status === 401) {
        if (endpoint.startsWith('/auth/login')) {
          let errorMsg = 'Credenciales inválidas';
          try {
            const errorData = await response.json();
            debugRequest({ url: safeUrl(url), method, status: response.status, body: redact(errorData) });
            errorMsg = errorData.detail || errorMsg;
          } catch {
            debugRequest({ url: safeUrl(url), method, status: response.status });
            errorMsg = 'Credenciales inválidas';
          }
          throw new Error(errorMsg);
        }
        this.clearToken();
        window.location.reload();
        return;
      }

      if (!response.ok) {
        let errorMsg = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.json();
          debugRequest({ url: safeUrl(url), method, status: response.status, body: redact(errorData) });
          errorMsg = errorData.detail || errorMsg;
        } catch {
          debugRequest({ url: safeUrl(url), method, status: response.status });
        }
        throw new Error(errorMsg);
      }

      const data = await response.json();
      debugRequest({ url: safeUrl(url), method, status: response.status, body: redact(data) });
      return data;
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
    }
  }

  // Auth endpoints
  async login(email, password) {
    return this.request(`/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, {
      method: 'POST'
    });
  }

  async getCurrentUser() {
    return this.request('/auth/me', { timeoutMs: 10000 });
  }

  async register(email, password, fullName) {
    return this.request(`/auth/register?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}&full_name=${encodeURIComponent(fullName)}`, {
      method: 'POST'
    });
  }

  // Module proxy calls
  async callModule(moduleName, endpoint, method = 'GET', data = null) {
    return this.request(`/api/${moduleName}/${endpoint}`, {
      method,
      body: data ? JSON.stringify(data) : null
    });
  }

  // Core system endpoints
  async getSystemStatus() {
    return this.request('/core/status');
  }

  async getModules() {
    return this.request('/core/modules');
  }
}

export const apiClient = new SIGAApiClient();

// WebSocket Client for real-time events
export class SIGAWSClient {
  constructor() {
    this.ws = null;
    this.listeners = {};
    this.connected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    if (this.ws && this.connected) {
      setTimeout(() => this.trigger('connected'), 0);
      return;
    }

    this.ws = new WebSocket(`${WS_BASE}/ws`);

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.connected = true;
      this.reconnectAttempts = 0;
      this.trigger('connected');
    };

    this.ws.onmessage = (event) => {
      console.log('📨 WS Message:', event.data);
      this.trigger('message', event.data);
    };

    this.ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      this.connected = false;
      this.trigger('disconnected');
      
      // Auto reconnect (if not intentionally closed)
      if (!this.intentionalDisconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
      }
      this.intentionalDisconnect = false;
    };
    
    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.intentionalDisconnect = true;
      this.ws.close();
      this.ws = null;
    }
  }

  send(data) {
    if (this.ws && this.connected) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    return () => {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    };
  }

  trigger(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }
}

export const wsClient = new SIGAWSClient();
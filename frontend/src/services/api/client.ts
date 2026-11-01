/**
 * ClearHire Centralized API Client
 * Built on native fetch with automatic Bearer token injection,
 * standardized ApiError normalization, and 401 interception.
 */

const TOKEN_STORAGE_KEY = 'clearhire_access_token';

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: ApiErrorDetail[] | unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export const getStoredToken = (): string | null => {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
};

export const setStoredToken = (token: string): void => {
  try {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    // Clean up any legacy shared tokens in localStorage to prevent cross-tab leaks
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.error('Failed to store auth token in sessionStorage:', err);
  }
};

export const removeStoredToken = (): void => {
  try {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.error('Failed to remove auth token from sessionStorage:', err);
  }
};

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
}

class ApiClient {
  private get baseUrl(): string {
    const envUrl = import.meta.env.VITE_API_BASE_URL;
    return (envUrl || 'http://localhost:8000/api/v1').replace(/\/+$/, '');
  }

  private buildUrl(path: string, params?: Record<string, string | number | boolean | undefined | null>): string {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const url = new URL(`${this.baseUrl}${cleanPath}`);

    if (params) {
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null) {
          url.searchParams.append(key, String(val));
        }
      });
    }

    return url.toString();
  }

  private async parseError(response: Response): Promise<ApiError> {
    const status = response.status;
    let message = `Request failed with status ${status}`;
    let code = 'HTTP_ERROR';
    let details: unknown = null;

    try {
      const data = await response.json();
      if (data && typeof data === 'object') {
        if (data.error && typeof data.error === 'object') {
          // ClearHire structured error format { error: { code, message, details } }
          code = data.error.code || code;
          message = data.error.message || message;
          details = data.error.details ?? null;

          if (Array.isArray(details) && details.length > 0) {
            const firstDetail = details[0] as ApiErrorDetail;
            if (firstDetail?.msg) {
              const field = firstDetail.loc ? firstDetail.loc[firstDetail.loc.length - 1] : '';
              message = field ? `${field}: ${firstDetail.msg}` : firstDetail.msg;
            }
          }
        } else if (data.detail) {
          // Standard FastAPI detail format
          if (typeof data.detail === 'string') {
            message = data.detail;
          } else if (Array.isArray(data.detail) && data.detail.length > 0) {
            details = data.detail;
            const firstDetail = data.detail[0] as ApiErrorDetail;
            const field = firstDetail.loc ? firstDetail.loc[firstDetail.loc.length - 1] : '';
            message = field ? `${field}: ${firstDetail.msg}` : (firstDetail.msg || message);
          }
        }
      }
    } catch {
      // Fallback if response is non-JSON
      if (response.statusText) {
        message = response.statusText;
      }
    }

    return new ApiError(message, status, code, details);
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { params, headers = {}, ...customConfig } = options;
    const url = this.buildUrl(path, params);

    const token = getStoredToken();
    const reqHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers as Record<string, string>),
    };

    // If body is FormData, do not set Content-Type header so the browser sets the boundary automatically
    if (customConfig.body instanceof FormData) {
      delete reqHeaders['Content-Type'];
    }

    const response = await fetch(url, {
      ...customConfig,
      headers: reqHeaders,
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeStoredToken();
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('clearhire:unauthorized'));
        }
      }
      throw await this.parseError(response);
    }

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    return (await response.json()) as T;
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' });
  }

  /**
   * Fetch binary Blob resource (e.g. PDF documents) with authentication and error handling.
   */
  async getBlob(
    path: string,
    options: RequestOptions = {}
  ): Promise<{ blob: Blob; filename: string; contentType: string }> {
    const { params, headers = {}, ...customConfig } = options;
    const url = this.buildUrl(path, params);

    const token = getStoredToken();
    const reqHeaders: Record<string, string> = {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers as Record<string, string>),
    };

    const response = await fetch(url, {
      ...customConfig,
      method: 'GET',
      headers: reqHeaders,
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeStoredToken();
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('clearhire:unauthorized'));
        }
      }
      throw await this.parseError(response);
    }

    const contentType = response.headers.get('content-type') || 'application/octet-stream';
    let filename = 'document.pdf';
    const disposition = response.headers.get('content-disposition');
    if (disposition) {
      const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
      if (match && match[1]) {
        filename = match[1].trim();
      }
    }

    const blob = await response.blob();
    return { blob, filename, contentType };
  }


  post<T>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data),
    });
  }

  put<T>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'PUT',
      body: data instanceof FormData ? data : JSON.stringify(data),
    });
  }

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();

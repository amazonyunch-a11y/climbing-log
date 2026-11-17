import { tokenStorage } from '@/src/auth/tokenStorage';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL?.trim().replace(/\/$/, '');
const isDevelopment = process.env.NODE_ENV !== 'production';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let unauthorizedHandler: (() => void | Promise<void>) | undefined;

export function setUnauthorizedHandler(handler: (() => void | Promise<void>) | undefined) {
  unauthorizedHandler = handler;
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (typeof payload === 'object' && payload !== null) {
      const message = (payload as { message?: unknown }).message;
      if (typeof message === 'string') return message;
      const detail = (payload as { detail?: unknown }).detail;
      if (typeof detail === 'string') return detail;
    }
  } catch {
    // Empty and non-JSON error responses use the fallback below.
  }

  return `Request failed (${response.status})`;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError('EXPO_PUBLIC_API_BASE_URL is not configured.', 0);
  }

  const token = await tokenStorage.get();
  const headers = new Headers(options.headers);
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const requestUrl = `${API_BASE_URL}${path}`;
  if (isDevelopment) console.info(`[API] ${options.method ?? 'GET'} ${requestUrl}`);

  let response: Response;
  try {
    response = await fetch(requestUrl, { ...options, headers });
  } catch (cause) {
    if (isDevelopment) console.warn(`[API] Network error for ${requestUrl}`, cause instanceof Error ? cause.message : cause);
    throw new ApiError('백엔드 서버에 연결할 수 없습니다. API 주소, Wi-Fi, 서버 실행 상태를 확인해 주세요.', 0);
  }

  if (isDevelopment) console.info(`[API] ${response.status} ${options.method ?? 'GET'} ${requestUrl}`);
  if (!response.ok) {
    const message = await getErrorMessage(response);
    if (response.status === 401) await unauthorizedHandler?.();
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

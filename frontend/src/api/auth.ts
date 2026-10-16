import { apiRequest } from '@/src/api/client';
import type { CurrentUser, LoginRequest, SignupRequest, SignupResponse, TokenResponse } from '@/src/types/auth';

export const authApi = {
  login: (payload: LoginRequest) =>
    apiRequest<TokenResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  signup: (payload: SignupRequest) =>
    apiRequest<SignupResponse>('/api/auth/signup', { method: 'POST', body: JSON.stringify(payload) }),
  me: () => apiRequest<CurrentUser>('/api/auth/me'),
  logout: () => apiRequest<void>('/api/auth/logout', { method: 'POST' }),
};

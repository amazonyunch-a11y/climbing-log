import { apiRequest } from '@/src/api/client';
import type {
  AuthMessageResponse,
  CurrentUser,
  EmailVerificationConfirmRequest,
  EmailVerificationConfirmResponse,
  EmailVerificationRequest,
  LoginRequest,
  PasswordResetConfirmRequest,
  PasswordResetRequest,
  SignupRequest,
  SignupResponse,
  TokenResponse,
} from '@/src/types/auth';

export const authApi = {
  login: (payload: LoginRequest) =>
    apiRequest<TokenResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  signup: (payload: SignupRequest) =>
    apiRequest<SignupResponse>('/api/auth/signup', { method: 'POST', body: JSON.stringify(payload) }),
  me: () => apiRequest<CurrentUser>('/api/auth/me'),
  logout: () => apiRequest<void>('/api/auth/logout', { method: 'POST' }),
  requestPasswordReset: (payload: PasswordResetRequest) =>
    apiRequest<AuthMessageResponse>('/api/auth/password-reset/request', { method: 'POST', body: JSON.stringify(payload) }),
  confirmPasswordReset: (payload: PasswordResetConfirmRequest) =>
    apiRequest<AuthMessageResponse>('/api/auth/password-reset/confirm', { method: 'POST', body: JSON.stringify(payload) }),
  requestEmailVerification: (payload: EmailVerificationRequest) =>
    apiRequest<AuthMessageResponse>('/api/auth/email-verification/request', { method: 'POST', body: JSON.stringify(payload) }),
  confirmEmailVerification: (payload: EmailVerificationConfirmRequest) =>
    apiRequest<EmailVerificationConfirmResponse>('/api/auth/email-verification/confirm', { method: 'POST', body: JSON.stringify(payload) }),
};

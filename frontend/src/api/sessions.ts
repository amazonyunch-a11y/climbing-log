import { apiRequest } from '@/src/api/client';
import type { Session, SessionCreateInput, SessionCreateResponse, SessionUpdateInput } from '@/src/types/session';

export const sessionsApi = {
  list: () => apiRequest<Session[]>('/api/sessions'),
  create: (payload: SessionCreateInput) => apiRequest<SessionCreateResponse>('/api/sessions', { method: 'POST', body: JSON.stringify(payload) }),
  get: (sessionId: number) => apiRequest<Session>(`/api/sessions/${sessionId}`),
  update: (sessionId: number, payload: SessionUpdateInput) => apiRequest<Session>(`/api/sessions/${sessionId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  remove: (sessionId: number) => apiRequest<void>(`/api/sessions/${sessionId}`, { method: 'DELETE' }),
};

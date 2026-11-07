import { apiRequest } from '@/src/api/client';
import type { Stopwatch } from '@/src/types/stopwatch';

export const stopwatchApi = {
  start: () => apiRequest<Stopwatch>('/api/stopwatch', { method: 'POST' }),
  getActive: () => apiRequest<Stopwatch>('/api/stopwatch/active'),
  stop: (stopwatchId: number) => apiRequest<Stopwatch>(`/api/stopwatch/${stopwatchId}/stop`, { method: 'PATCH' }),
  finish: (stopwatchId: number) => apiRequest<Stopwatch>(`/api/stopwatch/${stopwatchId}/finish`, { method: 'PATCH' }),
  reset: (stopwatchId: number) => apiRequest<Stopwatch>(`/api/stopwatch/${stopwatchId}/reset`, { method: 'PATCH' }),
  getPending: (sessionDate: string) => apiRequest<Stopwatch[]>(`/api/stopwatch/pending?session_date=${encodeURIComponent(sessionDate)}`),
};

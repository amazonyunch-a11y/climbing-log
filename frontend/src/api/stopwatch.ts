import { apiRequest } from '@/src/api/client';
import type { Stopwatch } from '@/src/types/stopwatch';

export const stopwatchApi = {
  start: () => apiRequest<Stopwatch>('/api/stopwatch', { method: 'POST' }),
  getActive: () => apiRequest<Stopwatch>('/api/stopwatch/active'),
  stop: (stopwatchId: number) => apiRequest<Stopwatch>(`/api/stopwatch/${stopwatchId}/stop`, { method: 'PATCH' }),
  reset: (stopwatchId: number) => apiRequest<Stopwatch>(`/api/stopwatch/${stopwatchId}/reset`, { method: 'PATCH' }),
};

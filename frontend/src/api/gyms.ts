import { apiRequest } from '@/src/api/client';
import type { Gym, GymCreateResponse, GymInput } from '@/src/types/gym';

export const gymsApi = {
  list: () => apiRequest<Gym[]>('/api/gyms'),
  get: (gymId: number) => apiRequest<Gym>(`/api/gyms/${gymId}`),
  create: (payload: GymInput) => apiRequest<GymCreateResponse>('/api/gyms', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  update: (gymId: number, payload: GymInput) => apiRequest<Gym>(`/api/gyms/${gymId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),
  remove: (gymId: number) => apiRequest<void>(`/api/gyms/${gymId}`, { method: 'DELETE' }),
};

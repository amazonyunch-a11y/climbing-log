import { apiRequest } from '@/src/api/client';
import type { Profile, ProfileUpdate } from '@/src/types/profile';

export const profileApi = {
  get: () => apiRequest<Profile>('/api/profile'),
  update: (payload: ProfileUpdate) =>
    apiRequest<Profile>('/api/profile', { method: 'PATCH', body: JSON.stringify(payload) }),
};

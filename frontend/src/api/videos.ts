import { apiRequest } from '@/src/api/client';
import type { SessionVideo, VideoCreateInput } from '@/src/types/video';

export const videosApi = {
  list: (sessionId: number) => apiRequest<SessionVideo[]>(`/api/sessions/${sessionId}/videos`),
  create: (sessionId: number, payload: VideoCreateInput) => apiRequest<SessionVideo>(`/api/sessions/${sessionId}/videos`, { method: 'POST', body: JSON.stringify(payload) }),
  remove: (videoId: number) => apiRequest<void>(`/api/videos/${videoId}`, { method: 'DELETE' }),
};

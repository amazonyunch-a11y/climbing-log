import { apiRequest } from '@/src/api/client';
import type { GradeLog, GradeLogInput } from '@/src/types/gradeLog';

export const gradeLogsApi = {
  list: (sessionId: number) => apiRequest<GradeLog[]>(`/api/sessions/${sessionId}/grades`),
  create: (sessionId: number, payload: GradeLogInput) => apiRequest<GradeLog>(`/api/sessions/${sessionId}/grades`, { method: 'POST', body: JSON.stringify(payload) }),
  update: (gradeId: number, payload: GradeLogInput) => apiRequest<GradeLog>(`/api/grades/${gradeId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  remove: (gradeId: number) => apiRequest<void>(`/api/grades/${gradeId}`, { method: 'DELETE' }),
};

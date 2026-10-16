import { apiRequest } from '@/src/api/client';
import type { CalendarDateResponse, CalendarMonthItem } from '@/src/types/calendar';

export const calendarApi = {
  month: (year: number, month: number) => apiRequest<CalendarMonthItem[]>(`/api/calendar?year=${year}&month=${month}`),
  date: (date: string) => apiRequest<CalendarDateResponse>(`/api/calendar/${date}`),
};

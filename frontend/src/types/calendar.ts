export type CalendarMonthItem = { date: string; session_count: number };

export type CalendarSession = {
  id: number;
  gym_name: string | null;
  duration_minutes: number | null;
  total_attempts: number;
  total_sends: number;
};

export type CalendarDateResponse = { date: string; sessions: CalendarSession[] };

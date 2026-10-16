export type Session = {
  id: number;
  gym_id: number;
  gym_name: string | null;
  session_date: string;
  started_at: string;
  ended_at: string | null;
  duration_minutes: number | null;
  total_attempts: number;
  total_sends: number;
  notes: string | null;
};

export type SessionCreateResponse = Omit<Session, 'gym_name'>;

export type SessionCreateInput = {
  gym_id: number;
  session_date: string;
  started_at: string;
  ended_at?: string | null;
  total_attempts: number;
  total_sends: number;
  notes?: string | null;
};

export type SessionUpdateInput = Partial<SessionCreateInput>;

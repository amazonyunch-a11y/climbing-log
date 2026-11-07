export type Stopwatch = {
  id: number;
  status: 'in_progress' | 'paused' | 'completed' | 'canceled';
  startedAt: string;
  endedAt: string | null;
  elapsedSeconds: number;
  linkedSessionId: number | null;
  sessionLinkStatus: 'unlinked' | 'linked' | 'pending' | 'ambiguous';
};

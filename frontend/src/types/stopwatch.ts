export type Stopwatch = {
  id: number;
  status: 'in_progress' | 'paused' | 'canceled';
  startedAt: string;
  endedAt: string | null;
  elapsedSeconds: number;
};

export type StatisticsPeriod = 'weekly' | 'monthly';

export type MonthlyStatisticsQuery = {
  period: 'monthly';
  year: number;
  month: number;
};

export type WeeklyStatisticsQuery = {
  period: 'weekly';
  start_date: string;
};

export type StatisticsQuery = MonthlyStatisticsQuery | WeeklyStatisticsQuery;

export type StatisticsSummary = {
  period: StatisticsPeriod;
  session_count: number;
  total_duration_minutes: number;
  total_attempts: number;
  total_sends: number;
  send_rate: number;
};

export type GradeStatistics = {
  grade_label: string | null;
  attempts: number;
  sends: number;
  send_rate: number;
};

export type GymStatistics = {
  gym_id: number;
  gym_name: string | null;
  visit_count: number;
};

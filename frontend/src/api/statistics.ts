import { apiRequest } from '@/src/api/client';
import type { GradeStatistics, GymStatistics, StatisticsQuery, StatisticsSummary } from '@/src/types/statistics';

function toQueryString(query: StatisticsQuery): string {
  const params = new URLSearchParams({ period: query.period });
  if (query.period === 'monthly') {
    params.set('year', String(query.year));
    params.set('month', String(query.month));
  } else {
    params.set('start_date', query.start_date);
  }
  return params.toString();
}

export const statisticsApi = {
  summary: (query: StatisticsQuery) => apiRequest<StatisticsSummary>(`/api/statistics/summary?${toQueryString(query)}`),
  grades: (query: StatisticsQuery) => apiRequest<GradeStatistics[]>(`/api/statistics/grades?${toQueryString(query)}`),
  gyms: (query: StatisticsQuery) => apiRequest<GymStatistics[]>(`/api/statistics/gyms?${toQueryString(query)}`),
};

import { statisticsApi } from '@/src/api/statistics';
import { ApiError } from '@/src/api/client';
import { LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { GradeStatistics, GymStatistics, StatisticsPeriod, StatisticsQuery, StatisticsSummary } from '@/src/types/statistics';
import { formatLocalDate, parseLocalDate } from '@/src/utils/date';
import { useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useRef, useState } from 'react';
import { RefreshControl, StyleSheet, View } from 'react-native';
import { Button, Card, Icon, IconButton, ProgressBar, SegmentedButtons, Snackbar, Text } from 'react-native-paper';

type StatisticsData = {
  summary?: StatisticsSummary;
  grades: GradeStatistics[];
  gyms: GymStatistics[];
};

function getWeekStart(date: Date): Date {
  const day = date.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + mondayOffset);
}

function addDays(value: string, days: number): string {
  const date = parseLocalDate(value);
  return formatLocalDate(new Date(date.getFullYear(), date.getMonth(), date.getDate() + days));
}

function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  if (hours === 0) return `${remaining}분`;
  return remaining === 0 ? `${hours}시간` : `${hours}시간 ${remaining}분`;
}

function formatRate(rate: number): string {
  return `${Number.isFinite(rate) ? rate.toFixed(1).replace(/\.0$/, '') : '0'}%`;
}

export default function StatisticsScreen() {
  const today = useMemo(() => new Date(), []);
  const [period, setPeriod] = useState<StatisticsPeriod>('monthly');
  const [visibleMonth, setVisibleMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [weekStart, setWeekStart] = useState(() => formatLocalDate(getWeekStart(today)));
  const [data, setData] = useState<StatisticsData>({ grades: [], gyms: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const requestId = useRef(0);

  const query = useMemo<StatisticsQuery>(() => period === 'monthly'
    ? { period, year: visibleMonth.getFullYear(), month: visibleMonth.getMonth() + 1 }
    : { period, start_date: weekStart }, [period, visibleMonth, weekStart]);

  const periodLabel = period === 'monthly'
    ? `${visibleMonth.getFullYear()}년 ${visibleMonth.getMonth() + 1}월`
    : `${weekStart} ~ ${addDays(weekStart, 6)}`;

  const refetch = useCallback(async () => {
    const currentRequestId = ++requestId.current;
    setLoading(true);
    setError(undefined);
    const [summary, grades, gyms] = await Promise.allSettled([
      statisticsApi.summary(query),
      statisticsApi.grades(query),
      statisticsApi.gyms(query),
    ]);

    if (currentRequestId !== requestId.current) return;
    const errors = [summary, grades, gyms]
      .filter((result): result is PromiseRejectedResult => result.status === 'rejected')
      .map((result) => result.reason instanceof ApiError ? result.reason.message : '통계 정보를 불러오지 못했습니다.');

    setData({
      summary: summary.status === 'fulfilled' ? summary.value : undefined,
      grades: grades.status === 'fulfilled' ? grades.value : [],
      gyms: gyms.status === 'fulfilled' ? gyms.value : [],
    });
    if (errors.length > 0) setError(errors[0]);
    setLoading(false);
  }, [query]);

  useFocusEffect(useCallback(() => { void refetch(); }, [refetch]));

  const changePeriod = (value: string) => {
    if (value === 'weekly' || value === 'monthly') setPeriod(value);
  };

  const movePeriod = (direction: number) => {
    if (period === 'monthly') {
      setVisibleMonth((current) => new Date(current.getFullYear(), current.getMonth() + direction, 1));
      return;
    }
    setWeekStart((current) => addDays(current, direction * 7));
  };

  const summaryItems = data.summary ? [
    ['운동 횟수', `${data.summary.session_count}회`],
    ['총 운동시간', formatDuration(data.summary.total_duration_minutes)],
    ['총 시도', `${data.summary.total_attempts}회`],
    ['총 완등', `${data.summary.total_sends}회`],
    ['완등률', formatRate(data.summary.send_rate)],
  ] : [];

  return <Screen scroll refreshControl={<RefreshControl refreshing={loading} onRefresh={() => void refetch()} tintColor={colors.blue600} colors={[colors.blue600]} />}>
    <PageHeader title="운동 통계" subtitle="기간별 운동 흐름을 한눈에 확인하세요." />
    <SegmentedButtons
      value={period}
      onValueChange={changePeriod}
      buttons={[{ value: 'monthly', label: '월간' }, { value: 'weekly', label: '주간' }]}
    />

    <View style={styles.periodNavigation}>
      <IconButton icon="chevron-left" onPress={() => movePeriod(-1)} accessibilityLabel="이전 기간" />
      <Text variant="titleMedium" style={styles.periodLabel}>{periodLabel}</Text>
      <IconButton icon="chevron-right" onPress={() => movePeriod(1)} accessibilityLabel="다음 기간" />
    </View>

    {loading && !data.summary ? <LoadingState label="통계를 불러오는 중입니다." /> : <>
      <Card mode="outlined" style={[uiStyles.card, styles.summaryCard]}>
        <Card.Content style={styles.cardContent}>
          <View style={styles.sectionTitle}><Icon source="chart-box-outline" size={24} color={colors.blue600} /><Text variant="titleLarge" style={styles.cardTitle}>운동 요약</Text></View>
          {summaryItems.length > 0 ? <View style={styles.summaryGrid}>{summaryItems.map(([label, value]) => <View key={label} style={styles.summaryItem}><Text variant="bodySmall" style={uiStyles.muted}>{label}</Text><Text variant="titleLarge" style={styles.summaryValue}>{value}</Text></View>)}</View> : <Text style={uiStyles.muted}>요약 정보를 불러오지 못했습니다.</Text>}
        </Card.Content>
      </Card>

      <Card mode="outlined" style={uiStyles.card}>
        <Card.Content style={styles.cardContent}>
          <View style={styles.sectionTitle}><Icon source="chart-timeline-variant" size={24} color={colors.blue600} /><Text variant="titleLarge" style={styles.cardTitle}>난이도별 통계</Text></View>
          {data.grades.length === 0 ? <View style={styles.empty}><Icon source="chart-bar-stacked" size={30} color={colors.textMuted} /><Text style={styles.emptyText}>이 기간에 난이도 기록이 없습니다.</Text></View> : data.grades.map((grade) => <View key={grade.grade_label ?? 'unlabeled'} style={styles.listItem}>
            <View style={styles.listTitleRow}><Text variant="titleMedium">{grade.grade_label ?? '난이도 미지정'}</Text><Text>{formatRate(grade.send_rate)}</Text></View>
            <Text>시도 {grade.attempts}회 · 완등 {grade.sends}회</Text>
            <ProgressBar progress={Math.max(0, Math.min(grade.send_rate / 100, 1))} style={styles.progress} />
          </View>)}
        </Card.Content>
      </Card>

      <Card mode="outlined" style={uiStyles.card}>
        <Card.Content style={styles.cardContent}>
          <View style={styles.sectionTitle}><Icon source="map-marker-radius-outline" size={24} color={colors.blue600} /><Text variant="titleLarge" style={styles.cardTitle}>암장별 방문</Text></View>
          {data.gyms.length === 0 ? <View style={styles.empty}><Icon source="map-marker-off-outline" size={30} color={colors.textMuted} /><Text style={styles.emptyText}>이 기간에 방문한 암장이 없습니다.</Text></View> : data.gyms.map((gym) => <View key={gym.gym_id} style={styles.gymRow}><Text variant="titleMedium" style={styles.gymName} numberOfLines={2}>{gym.gym_name ?? '암장 정보 없음'}</Text><View style={styles.visitBadge}><Text variant="labelLarge" style={styles.visitText}>{gym.visit_count}회</Text></View></View>)}
        </Card.Content>
      </Card>
    </>}

    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)} action={{ label: '재시도', onPress: () => void refetch() }}>{error}</Snackbar>
    {!loading && Boolean(error) && <Button mode="outlined" onPress={() => void refetch()}>다시 시도</Button>}
  </Screen>;
}

const styles = StyleSheet.create({
  periodNavigation: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border },
  periodLabel: { flex: 1, textAlign: 'center', color: colors.navy900, fontWeight: '700' },
  cardContent: { gap: spacing.lg }, sectionTitle: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm }, cardTitle: { color: colors.navy900, fontWeight: '700' },
  summaryCard: { borderRadius: radius.lg }, summaryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  summaryItem: { width: '48%', flexGrow: 1, minHeight: 86, gap: spacing.xs, padding: spacing.md, borderRadius: radius.md, backgroundColor: colors.surfaceMuted },
  summaryValue: { color: colors.blue700, fontWeight: '800' },
  listItem: { gap: spacing.sm, paddingVertical: spacing.md, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  listTitleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  progress: { height: 7, borderRadius: 4 },
  gymRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: spacing.md, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, gap: spacing.md }, gymName: { flex: 1 }, visitBadge: { paddingHorizontal: spacing.md, paddingVertical: spacing.xs, borderRadius: radius.pill, backgroundColor: colors.blue100 }, visitText: { color: colors.blue700 },
  empty: { minHeight: 120, alignItems: 'center', justifyContent: 'center', gap: spacing.sm }, emptyText: { color: colors.textMuted, textAlign: 'center' },
});

import { calendarApi } from '@/src/api/calendar';
import { ApiError } from '@/src/api/client';
import { EmptyState, LoadingState, PageHeader, Screen, SectionHeader, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import { createMonthGrid, formatKoreanDate, formatKstDate, formatLocalDate, parseLocalDate } from '@/src/utils/date';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Button, Card, Icon, IconButton, Snackbar, Text } from 'react-native-paper';

export default function CalendarScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ date?: string }>();
  const today = useMemo(() => parseLocalDate(formatKstDate(new Date())), []);
  const [visibleMonth, setVisibleMonth] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [selectedDate, setSelectedDate] = useState(formatLocalDate(today));
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [sessions, setSessions] = useState<Awaited<ReturnType<typeof calendarApi.date>>['sessions']>([]);
  const [isDailyLoading, setIsDailyLoading] = useState(true);
  const [error, setError] = useState<string>();
  const dailyRequestId = useRef(0);
  const monthRequestId = useRef(0);

  useEffect(() => {
    if (!params.date) return;
    const [year, month] = params.date.split('-').map(Number);
    if (year && month) setVisibleMonth(new Date(year, month - 1, 1));
    setSelectedDate(params.date);
  }, [params.date]);

  const refetchMonth = useCallback(async (month: Date) => {
    const requestId = ++monthRequestId.current;
    try {
      const monthly = await calendarApi.month(month.getFullYear(), month.getMonth() + 1);
      if (requestId === monthRequestId.current) setCounts(Object.fromEntries(monthly.map((item) => [item.date, item.session_count])));
    } catch (cause) { if (requestId === monthRequestId.current) setError(cause instanceof ApiError ? cause.message : '월간 운동 기록을 불러오지 못했습니다.'); }
  }, []);

  const refetchDailySessions = useCallback(async (date: string) => {
    const requestId = ++dailyRequestId.current;
    setIsDailyLoading(true); setSessions([]); setError(undefined);
    try {
      const daily = await calendarApi.date(date);
      if (daily.date !== date) throw new ApiError('선택한 날짜와 다른 세션 응답을 받았습니다.', 500);
      if (requestId === dailyRequestId.current) setSessions(daily.sessions);
    } catch (cause) { if (requestId === dailyRequestId.current) setError(cause instanceof ApiError ? cause.message : '날짜별 세션을 불러오지 못했습니다.'); }
    finally { if (requestId === dailyRequestId.current) setIsDailyLoading(false); }
  }, []);

  useFocusEffect(useCallback(() => {
    void refetchMonth(visibleMonth);
    void refetchDailySessions(selectedDate);
  }, [refetchDailySessions, refetchMonth, selectedDate, visibleMonth]));

  const selectDate = (date: string) => {
    if (date === selectedDate) {
      void refetchDailySessions(date);
      return;
    }
    dailyRequestId.current += 1;
    setSessions([]);
    setIsDailyLoading(true);
    setSelectedDate(date);
    const value = new Date(Number(date.slice(0, 4)), Number(date.slice(5, 7)) - 1, 1);
    if (value.getMonth() !== visibleMonth.getMonth() || value.getFullYear() !== visibleMonth.getFullYear()) setVisibleMonth(value);
  };
  const changeMonth = (delta: number) => {
    const nextMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + delta, 1);
    dailyRequestId.current += 1;
    monthRequestId.current += 1;
    setSessions([]); setCounts({}); setIsDailyLoading(true);
    setVisibleMonth(nextMonth);
    setSelectedDate(formatLocalDate(nextMonth));
  };
  const grid = createMonthGrid(visibleMonth.getFullYear(), visibleMonth.getMonth());
  const monthTitle = `${visibleMonth.getFullYear()}년 ${visibleMonth.getMonth() + 1}월`;

  return <Screen scroll>
    <PageHeader title="운동 캘린더" subtitle="날짜별 클라이밍 기록을 확인하세요." />
    <Card mode="outlined" style={[uiStyles.card, styles.calendarCard]}><Card.Content style={styles.cardContent}>
      <View style={styles.monthHeader}><IconButton icon="chevron-left" onPress={() => changeMonth(-1)} /><Text variant="titleLarge">{monthTitle}</Text><IconButton icon="chevron-right" onPress={() => changeMonth(1)} /></View>
      <View style={styles.weekRow}>{['일', '월', '화', '수', '목', '금', '토'].map((day) => <Text key={day} style={styles.weekday}>{day}</Text>)}</View>
      <View style={styles.grid}>{grid.map((day) => {
        const isSelected = day.dateString === selectedDate; const isToday = day.dateString === formatLocalDate(today); const count = counts[day.dateString] ?? 0;
        return <Pressable key={day.dateString} style={styles.cell} onPress={() => selectDate(day.dateString)} accessibilityRole="button" accessibilityLabel={`${formatKoreanDate(day.dateString)}, 세션 ${count}개`}><View style={[styles.dayCircle, isSelected && styles.selectedDay, isToday && !isSelected && styles.todayDay]}><Text style={[styles.dayText, !day.isCurrentMonth && styles.otherMonth, isSelected && styles.selectedText]}>{day.date.getDate()}</Text></View>{count > 0 && <View style={[styles.countDot, isSelected && styles.countDotSelected]} />}</Pressable>;
      })}</View>
    </Card.Content></Card>
    <SectionHeader title={formatKoreanDate(selectedDate)} description="선택한 날짜의 운동 기록" action={<Button mode="contained" icon="plus" compact onPress={() => router.push({ pathname: '/calendar/sessions/new', params: { date: selectedDate } })}>세션 추가</Button>} />
    {isDailyLoading ? <LoadingState label="세션을 불러오는 중입니다." /> : sessions.length === 0 ? <EmptyState title="이 날짜의 운동 기록이 없어요" description="첫 세션을 추가해 운동을 기록해 보세요." icon="calendar-blank-outline" action={<Button mode="contained-tonal" onPress={() => router.push({ pathname: '/calendar/sessions/new', params: { date: selectedDate } })}>세션 추가</Button>} /> : sessions.map((session) => <Card key={session.id} mode="outlined" style={uiStyles.card} onPress={() => router.push({ pathname: '/calendar/sessions/[sessionId]', params: { sessionId: String(session.id) } })}><Card.Content style={styles.sessionCard}><View style={styles.sessionTitle}><View style={styles.sessionIcon}><Icon source="map-marker-outline" size={22} color={colors.blue600} /></View><Text variant="titleMedium" style={styles.sessionName} numberOfLines={2}>{session.gym_name ?? '암장 정보 없음'}</Text><Icon source="chevron-right" size={22} color={colors.textMuted} /></View><View style={styles.metrics}><Text variant="bodyMedium">{session.duration_minutes ?? '-'}분</Text><Text variant="bodyMedium">시도 {session.total_attempts}</Text><Text variant="bodyMedium">완등 {session.total_sends}</Text></View></Card.Content></Card>)}
    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)} action={{ label: '다시 시도', onPress: () => { void refetchMonth(visibleMonth); void refetchDailySessions(selectedDate); } }}>{error}</Snackbar>
  </Screen>;
}

const styles = StyleSheet.create({
  calendarCard: { borderRadius: radius.lg },
  cardContent: { gap: spacing.md },
  monthHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  weekRow: { flexDirection: 'row' }, weekday: { width: '14.285%', textAlign: 'center', color: colors.textMuted, fontWeight: '700' },
  grid: { flexDirection: 'row', flexWrap: 'wrap' }, cell: { width: '14.285%', minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  dayCircle: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center', borderRadius: radius.pill },
  selectedDay: { backgroundColor: colors.navy900 }, todayDay: { borderWidth: 1.5, borderColor: colors.blue600 },
  dayText: { color: colors.text, fontSize: 15 }, otherMonth: { opacity: 0.32 }, selectedText: { color: '#FFFFFF', fontWeight: '700' },
  countDot: { width: 5, height: 5, borderRadius: 3, backgroundColor: colors.sky500, marginTop: 1 }, countDotSelected: { backgroundColor: colors.navy900 },
  sessionCard: { gap: spacing.md }, sessionTitle: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm }, sessionName: { flex: 1, color: colors.navy900, fontWeight: '700' },
  sessionIcon: { width: 38, height: 38, borderRadius: radius.md, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.lg, paddingLeft: 46 },
});

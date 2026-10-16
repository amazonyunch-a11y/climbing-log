import { stopwatchApi } from '@/src/api/stopwatch';
import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { EmptyState, PageHeader, Screen, SectionHeader, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { Stopwatch } from '@/src/types/stopwatch';
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { ActivityIndicator, Button, Card, Icon, Snackbar, Text } from 'react-native-paper';

function formatElapsed(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return [hours, minutes, remainingSeconds].map((value) => String(value).padStart(2, '0')).join(':');
}

function currentElapsed(stopwatch: Stopwatch, syncedAt: number): number {
  if (stopwatch.status !== 'in_progress') return stopwatch.elapsedSeconds;
  return stopwatch.elapsedSeconds + Math.max(0, Math.floor((Date.now() - syncedAt) / 1000));
}

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [stopwatch, setStopwatch] = useState<Stopwatch>();
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [syncedAt, setSyncedAt] = useState(0);
  const [isLoadingStopwatch, setIsLoadingStopwatch] = useState(true);
  const [isUpdatingStopwatch, setIsUpdatingStopwatch] = useState(false);
  const [error, setError] = useState<string>();

  const loadActiveStopwatch = useCallback(async () => {
    setIsLoadingStopwatch(true);
    setError(undefined);
    try {
      const active = await stopwatchApi.getActive();
      setStopwatch(active);
      setElapsedSeconds(active.elapsedSeconds);
      setSyncedAt(Date.now());
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 404) {
        setStopwatch(undefined);
        setElapsedSeconds(0);
        setSyncedAt(0);
      } else {
        setError(cause instanceof ApiError ? cause.message : '스톱워치를 불러오지 못했습니다.');
      }
    } finally {
      setIsLoadingStopwatch(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void loadActiveStopwatch(); }, [loadActiveStopwatch]));

  useEffect(() => {
    if (stopwatch?.status !== 'in_progress') return;
    const timer = setInterval(() => setElapsedSeconds(currentElapsed(stopwatch, syncedAt)), 1000);
    return () => clearInterval(timer);
  }, [stopwatch, syncedAt]);

  const startStopwatch = async () => {
    setIsUpdatingStopwatch(true); setError(undefined);
    try {
      const started = await stopwatchApi.start();
      setStopwatch(started); setElapsedSeconds(started.elapsedSeconds); setSyncedAt(Date.now());
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '스톱워치를 시작하지 못했습니다.');
    } finally { setIsUpdatingStopwatch(false); }
  };

  const stopStopwatch = async () => {
    if (!stopwatch) return;
    setIsUpdatingStopwatch(true); setError(undefined);
    try {
      const paused = await stopwatchApi.stop(stopwatch.id);
      setStopwatch(paused); setElapsedSeconds(paused.elapsedSeconds); setSyncedAt(0);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '스톱워치를 일시정지하지 못했습니다.');
    } finally { setIsUpdatingStopwatch(false); }
  };

  const resetStopwatch = async () => {
    if (!stopwatch) return;
    setIsUpdatingStopwatch(true); setError(undefined);
    try {
      await stopwatchApi.reset(stopwatch.id);
      setStopwatch(undefined); setElapsedSeconds(0); setSyncedAt(0);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '스톱워치를 초기화하지 못했습니다.');
    } finally { setIsUpdatingStopwatch(false); }
  };

  const statusLabel = stopwatch?.status === 'in_progress' ? '측정 중' : stopwatch?.status === 'paused' ? '일시정지' : '준비됨';
  return <Screen scroll>
    <PageHeader title={`${user?.nickname ?? '클라이머'}님, 반가워요`} subtitle="오늘도 안전하고 즐거운 등반 되세요." />
    <Card mode="outlined" style={[uiStyles.card, styles.stopwatchCard]}><Card.Content style={styles.cardContent}>
      <View style={styles.cardHeader}><View style={styles.iconBox}><Icon source="timer-outline" size={26} color={colors.blue600} /></View><View style={styles.cardHeaderText}><Text variant="titleLarge" style={styles.cardTitle}>운동 스톱워치</Text><Text variant="bodySmall" style={uiStyles.muted}>운동 시간을 간편하게 측정하세요.</Text></View><View style={[styles.statusPill, stopwatch?.status === 'in_progress' && styles.statusActive]}><Text variant="labelMedium" style={stopwatch?.status === 'in_progress' ? styles.statusActiveText : uiStyles.muted}>{statusLabel}</Text></View></View>
      {isLoadingStopwatch ? <View style={styles.loading}><ActivityIndicator /><Text style={uiStyles.muted}>스톱워치 상태를 확인하는 중입니다.</Text></View> : <>
        <Text variant="displayMedium" style={styles.stopwatchTime}>{formatElapsed(elapsedSeconds)}</Text>
        <Text variant="bodyMedium" style={styles.stopwatchStatus}>{stopwatch?.status === 'in_progress' ? '현재 운동 시간을 기록하고 있습니다.' : stopwatch?.status === 'paused' ? '멈춘 시간부터 다시 이어갈 수 있습니다.' : 'Start를 눌러 측정을 시작해 보세요.'}</Text>
        {stopwatch?.status === 'in_progress' ? <View style={styles.stopwatchActions}>
          <Button mode="contained" icon="pause" onPress={() => void stopStopwatch()} loading={isUpdatingStopwatch} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>일시정지</Button>
          <Button mode="outlined" icon="restart" onPress={() => void resetStopwatch()} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>초기화</Button>
        </View> : <View style={styles.stopwatchActions}><Button mode="contained" icon="play" onPress={() => void startStopwatch()} loading={isUpdatingStopwatch} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>{stopwatch?.status === 'paused' ? '이어하기' : '시작'}</Button>{stopwatch?.status === 'paused' && <Button mode="outlined" icon="restart" onPress={() => void resetStopwatch()} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>초기화</Button>}</View>}
      </>}
    </Card.Content></Card>
    <SectionHeader title="오늘의 기록" description="캘린더에서 운동 세션을 관리할 수 있어요." />
    <EmptyState title="아직 표시할 운동이 없어요" description="오늘의 운동 기록을 캘린더에 추가해 보세요." icon="calendar-plus" action={<Button mode="contained-tonal" icon="plus" onPress={() => router.push('/calendar')}>운동 기록하기</Button>} />
    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)}>{error}</Snackbar>
  </Screen>;
}

const styles = StyleSheet.create({
  stopwatchCard: { borderRadius: radius.lg },
  cardContent: { gap: spacing.lg, paddingVertical: spacing.sm },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  cardHeaderText: { flex: 1, gap: 2 },
  cardTitle: { color: colors.navy900, fontWeight: '700' },
  iconBox: { width: 46, height: 46, borderRadius: radius.md, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' },
  statusPill: { paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, borderRadius: radius.pill, backgroundColor: colors.surfaceMuted },
  statusActive: { backgroundColor: colors.successContainer },
  statusActiveText: { color: colors.success, fontWeight: '700' },
  loading: { minHeight: 132, alignItems: 'center', justifyContent: 'center', gap: spacing.sm },
  stopwatchTime: { color: colors.navy950, fontVariant: ['tabular-nums'], fontWeight: '800', textAlign: 'center', letterSpacing: 1.5 },
  stopwatchStatus: { color: colors.textMuted, textAlign: 'center' },
  stopwatchActions: { flexDirection: 'row', gap: spacing.sm },
  actionButton: { flex: 1 },
});

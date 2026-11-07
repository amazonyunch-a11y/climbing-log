import { stopwatchApi } from '@/src/api/stopwatch';
import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { ConfirmDialog, EmptyState, PageHeader, Screen, SectionHeader, uiStyles } from '@/src/components/ui';
import { StopwatchPendingNotice } from '@/src/components/StopwatchPendingNotice';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { Stopwatch } from '@/src/types/stopwatch';
import { formatKstDate } from '@/src/utils/date';
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AppState, StyleSheet, View } from 'react-native';
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

type PendingAction = 'finish' | 'reset' | undefined;

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const today = useMemo(() => formatKstDate(new Date()), []);
  const [stopwatch, setStopwatch] = useState<Stopwatch>();
  const [pendingStopwatches, setPendingStopwatches] = useState<Stopwatch[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [syncedAt, setSyncedAt] = useState(0);
  const [isLoadingStopwatch, setIsLoadingStopwatch] = useState(true);
  const [isUpdatingStopwatch, setIsUpdatingStopwatch] = useState(false);
  const [pendingError, setPendingError] = useState<string>();
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<string>();
  const [confirmAction, setConfirmAction] = useState<PendingAction>();

  const loadActiveStopwatch = useCallback(async () => {
    setIsLoadingStopwatch(true);
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

  const loadPendingStopwatches = useCallback(async () => {
    try {
      setPendingStopwatches(await stopwatchApi.getPending(today));
      setPendingError(undefined);
    } catch (cause) {
      setPendingError(cause instanceof ApiError ? cause.message : '저장된 운동 시간을 확인하지 못했습니다.');
    }
  }, [today]);

  const refresh = useCallback(() => {
    void loadActiveStopwatch();
    void loadPendingStopwatches();
  }, [loadActiveStopwatch, loadPendingStopwatches]);

  useFocusEffect(useCallback(() => { refresh(); }, [refresh]));

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') refresh();
    });
    return () => subscription.remove();
  }, [refresh]);

  useEffect(() => {
    if (stopwatch?.status !== 'in_progress') return;
    const timer = setInterval(() => setElapsedSeconds(currentElapsed(stopwatch, syncedAt)), 1000);
    return () => clearInterval(timer);
  }, [stopwatch, syncedAt]);

  const updateStopwatch = (next: Stopwatch) => {
    setStopwatch(next);
    setElapsedSeconds(next.elapsedSeconds);
    setSyncedAt(next.status === 'in_progress' ? Date.now() : 0);
  };

  const startStopwatch = async () => {
    setIsUpdatingStopwatch(true); setError(undefined);
    try { updateStopwatch(await stopwatchApi.start()); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '스톱워치를 시작하지 못했습니다.'); } finally { setIsUpdatingStopwatch(false); }
  };

  const stopStopwatch = async () => {
    if (!stopwatch) return;
    setIsUpdatingStopwatch(true); setError(undefined);
    try { updateStopwatch(await stopwatchApi.stop(stopwatch.id)); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '스톱워치를 일시정지하지 못했습니다.'); } finally { setIsUpdatingStopwatch(false); }
  };

  const finishStopwatch = async () => {
    if (!stopwatch) return;
    setIsUpdatingStopwatch(true); setError(undefined);
    try {
      const finished = await stopwatchApi.finish(stopwatch.id);
      updateStopwatch(finished);
      setSuccess(finished.sessionLinkStatus === 'linked' ? '오늘 운동 세션에 자동으로 연결되었습니다.' : finished.sessionLinkStatus === 'ambiguous' ? '오늘 세션이 여러 개라 자동으로 연결하지 못했습니다.' : '운동 시간은 저장되었습니다. 오늘 세션을 추가하면 자동으로 연결됩니다.');
      await loadPendingStopwatches();
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : '운동 종료 및 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.'); } finally { setIsUpdatingStopwatch(false); setConfirmAction(undefined); }
  };

  const resetStopwatch = async () => {
    if (!stopwatch) return;
    setIsUpdatingStopwatch(true); setError(undefined);
    try {
      await stopwatchApi.reset(stopwatch.id);
      setStopwatch(undefined); setElapsedSeconds(0); setSyncedAt(0);
      setSuccess('스톱워치 기록을 초기화했습니다.');
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : '스톱워치를 초기화하지 못했습니다.'); } finally { setIsUpdatingStopwatch(false); setConfirmAction(undefined); }
  };

  const status = stopwatch?.status;
  const statusLabel = status === 'in_progress' ? '측정 중' : status === 'paused' ? '일시정지' : status === 'completed' ? '저장 완료' : '준비됨';
  const statusStyle = status === 'in_progress' ? styles.statusProgress : status === 'paused' ? styles.statusPaused : status === 'completed' ? styles.statusCompleted : undefined;
  const statusTextStyle = status === 'in_progress' ? styles.statusProgressText : status === 'paused' ? styles.statusPausedText : status === 'completed' ? styles.statusCompletedText : uiStyles.muted;
  const completedMessage = stopwatch?.sessionLinkStatus === 'linked' ? '오늘 운동 세션에 자동으로 연결되었습니다.' : stopwatch?.sessionLinkStatus === 'ambiguous' ? '오늘 세션이 여러 개라 자동으로 연결하지 못했습니다.' : '운동 시간은 저장되었습니다. 오늘 세션을 추가하면 자동으로 연결됩니다.';

  return <Screen scroll>
    <PageHeader title={`${user?.nickname ?? '클라이머'}님, 반가워요`} subtitle="오늘도 안전하고 즐거운 등반 되세요." />
    <Card mode="outlined" style={[uiStyles.card, styles.stopwatchCard]}><Card.Content style={styles.cardContent}>
      <View style={styles.cardHeader}><View style={styles.iconBox}><Icon source="timer-outline" size={26} color={colors.blue600} /></View><View style={styles.cardHeaderText}><Text variant="titleLarge" style={styles.cardTitle}>운동 스톱워치</Text><Text variant="bodySmall" style={uiStyles.muted}>운동 시간을 간편하게 측정하세요.</Text></View><View style={[styles.statusPill, statusStyle]}><Text variant="labelMedium" style={statusTextStyle}>{statusLabel}</Text></View></View>
      {isLoadingStopwatch ? <View style={styles.loading}><ActivityIndicator /><Text style={uiStyles.muted}>스톱워치 상태를 확인하는 중입니다.</Text></View> : <>
        <Text variant="displayMedium" style={styles.stopwatchTime}>{formatElapsed(elapsedSeconds)}</Text>
        <Text variant="bodyMedium" style={styles.stopwatchStatus}>{status === 'in_progress' ? '현재 운동 시간을 기록하고 있습니다.' : status === 'paused' ? '멈춘 시간부터 다시 이어갈 수 있습니다.' : status === 'completed' ? completedMessage : '운동 시작을 눌러 측정을 시작해 보세요.'}</Text>
        {status === 'in_progress' && <View style={styles.stopwatchActions}><Button mode="contained" icon="pause" onPress={() => void stopStopwatch()} loading={isUpdatingStopwatch} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>일시정지</Button><Button mode="contained-tonal" icon="check" onPress={() => setConfirmAction('finish')} loading={isUpdatingStopwatch} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>운동 종료 및 저장</Button><Button mode="outlined" icon="restart" textColor={colors.error} onPress={() => setConfirmAction('reset')} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>초기화</Button></View>}
        {status === 'paused' && <View style={styles.stopwatchActions}><Button mode="contained" icon="play" onPress={() => void startStopwatch()} loading={isUpdatingStopwatch} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>이어하기</Button><Button mode="contained-tonal" icon="check" onPress={() => setConfirmAction('finish')} loading={isUpdatingStopwatch} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>운동 종료 및 저장</Button><Button mode="outlined" icon="restart" textColor={colors.error} onPress={() => setConfirmAction('reset')} disabled={isUpdatingStopwatch} style={styles.actionButton} contentStyle={uiStyles.primaryButton}>초기화</Button></View>}
        {!status && <Button mode="contained" icon="play" onPress={() => void startStopwatch()} loading={isUpdatingStopwatch} disabled={isUpdatingStopwatch} contentStyle={uiStyles.primaryButton}>운동 시작</Button>}
        {status === 'completed' && stopwatch && <Button mode="outlined" icon={stopwatch.linkedSessionId ? 'text-box-search-outline' : 'calendar-plus'} onPress={() => stopwatch.linkedSessionId ? router.push({ pathname: '/calendar/sessions/[sessionId]', params: { sessionId: String(stopwatch.linkedSessionId) } }) : router.push({ pathname: '/calendar', params: { date: today } })} contentStyle={uiStyles.primaryButton}>{stopwatch.linkedSessionId ? '연결된 세션 상세보기' : '캘린더에서 세션 추가'}</Button>}
      </>}
    </Card.Content></Card>
    {pendingStopwatches.length > 0 && <StopwatchPendingNotice stopwatches={pendingStopwatches} action={<Button mode="contained-tonal" icon="calendar-plus" onPress={() => router.push({ pathname: '/calendar', params: { date: today } })}>오늘 세션 추가하기</Button>} />}
    {pendingError && <Card mode="outlined" style={styles.pendingError}><Card.Content style={styles.pendingErrorContent}><Text variant="bodySmall" style={uiStyles.muted}>저장된 운동 시간을 확인하지 못했습니다.</Text><Button compact onPress={() => void loadPendingStopwatches()}>다시 시도</Button></Card.Content></Card>}
    {pendingStopwatches.length === 0 && <><SectionHeader title="오늘의 기록" description="캘린더에서 운동 세션을 관리할 수 있어요." /><EmptyState title="아직 표시할 운동이 없어요" description="오늘의 운동 기록을 캘린더에 추가해 보세요." icon="calendar-plus" action={<Button mode="contained-tonal" icon="plus" onPress={() => router.push('/calendar')}>운동 기록하기</Button>} /></>}
    <ConfirmDialog visible={confirmAction === 'finish'} title="운동 종료 및 저장" message="현재까지 측정한 운동 시간을 저장할까요? 오늘 세션이 하나면 자동으로 연결됩니다." confirmLabel="저장" busy={isUpdatingStopwatch} onCancel={() => setConfirmAction(undefined)} onConfirm={() => void finishStopwatch()} />
    <ConfirmDialog visible={confirmAction === 'reset'} title="스톱워치 초기화" message="측정 중인 운동 시간을 폐기할까요? 이 기록은 세션에 사용되지 않습니다." confirmLabel="초기화" busy={isUpdatingStopwatch} onCancel={() => setConfirmAction(undefined)} onConfirm={() => void resetStopwatch()} />
    <Snackbar visible={Boolean(success)} onDismiss={() => setSuccess(undefined)}>{success}</Snackbar>
    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)}>{error}</Snackbar>
  </Screen>;
}

const styles = StyleSheet.create({
  stopwatchCard: { borderRadius: radius.lg }, cardContent: { gap: spacing.lg, paddingVertical: spacing.sm },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md }, cardHeaderText: { flex: 1, gap: 2 }, cardTitle: { color: colors.navy900, fontWeight: '700' }, iconBox: { width: 46, height: 46, borderRadius: radius.md, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' },
  statusPill: { paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, borderRadius: radius.pill, backgroundColor: colors.surfaceMuted }, statusProgress: { backgroundColor: colors.blue100 }, statusPaused: { backgroundColor: '#FFF0D5' }, statusCompleted: { backgroundColor: colors.successContainer }, statusProgressText: { color: colors.blue700, fontWeight: '700' }, statusPausedText: { color: colors.warning, fontWeight: '700' }, statusCompletedText: { color: colors.success, fontWeight: '700' },
  loading: { minHeight: 132, alignItems: 'center', justifyContent: 'center', gap: spacing.sm }, stopwatchTime: { color: colors.navy950, fontVariant: ['tabular-nums'], fontWeight: '800', textAlign: 'center', letterSpacing: 1.5 }, stopwatchStatus: { color: colors.textMuted, textAlign: 'center', lineHeight: 21 }, stopwatchActions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }, actionButton: { flexGrow: 1 },
  pendingError: { borderColor: colors.border }, pendingErrorContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
});

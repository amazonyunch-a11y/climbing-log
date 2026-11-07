import { ApiError } from '@/src/api/client';
import { sessionsApi } from '@/src/api/sessions';
import { GradeLogSection, type GradeTotals } from '@/src/components/GradeLogSection';
import { SessionVideoSection } from '@/src/components/SessionVideoSection';
import { ConfirmDialog, ErrorState, LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { Session } from '@/src/types/session';
import { formatKstDateTime } from '@/src/utils/date';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Icon, Snackbar, Text } from 'react-native-paper';

export default function SessionDetailScreen() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const id = Number(sessionId);
  const [session, setSession] = useState<Session>();
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteDialogVisible, setDeleteDialogVisible] = useState(false);
  const [error, setError] = useState<string>();
  const goBack = () => router.canGoBack() ? router.back() : router.replace('/calendar');
  const load = useCallback(async (showLoading = true) => {
    if (!Number.isInteger(id)) { setError('잘못된 세션 ID입니다.'); if (showLoading) setIsLoading(false); return; }
    if (showLoading) { setIsLoading(true); setError(undefined); }
    try { setSession(await sessionsApi.get(id)); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '세션을 불러오지 못했습니다.'); } finally { if (showLoading) setIsLoading(false); }
  }, [id]);
  useFocusEffect(useCallback(() => { void load(); }, [load]));
  const confirmDelete = async () => { setIsDeleting(true); try { await sessionsApi.remove(id); setDeleteDialogVisible(false); goBack(); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '세션을 삭제하지 못했습니다.'); } finally { setIsDeleting(false); } };
  const handleGradeLogsChanged = (totals?: GradeTotals) => {
    if (totals) setSession((current) => current && { ...current, total_attempts: totals.totalAttempts, total_sends: totals.totalSends });
    void load(false);
  };
  if (isLoading) return <Screen><PageHeader title="세션 상세" onBack={goBack} /><LoadingState label="세션 정보를 불러오는 중입니다." /></Screen>;
  if (!session) return <Screen><PageHeader title="세션 상세" onBack={goBack} /><ErrorState message={error ?? '세션을 찾을 수 없습니다.'} onRetry={() => void load()} /></Screen>;
  const detailItems = [
    { icon: 'calendar-outline', label: '운동 날짜', value: session.session_date },
    { icon: 'clock-start', label: '시작 시간', value: formatKstDateTime(session.started_at) },
    { icon: 'clock-end', label: '종료 시간', value: formatKstDateTime(session.ended_at) },
    { icon: 'timer-sand', label: '운동 시간', value: `${session.duration_minutes ?? '-'}분` },
    { icon: session.duration_source === 'stopwatch' ? 'timer-check-outline' : 'pencil-outline', label: '운동 시간 출처', value: session.duration_source === 'stopwatch' ? '스톱워치 기록' : '직접 입력' },
    { icon: 'link-variant', label: '스톱워치 연결', value: session.stopwatch_id ? `연결됨 (#${session.stopwatch_id})` : '연결되지 않음' },
  ];
  return <Screen scroll>
    <PageHeader title="세션 상세" subtitle="운동 기록과 난이도, 영상을 확인하세요." onBack={goBack} action={<Button mode="text" icon="pencil-outline" onPress={() => router.push({ pathname: '/calendar/sessions/[sessionId]/edit', params: { sessionId: String(session.id) } })}>수정</Button>} />
    <Card mode="outlined" style={[uiStyles.card, styles.heroCard]}><Card.Content style={styles.card}>
      <View style={styles.gymHeader}><View style={styles.gymIcon}><Icon source="map-marker" size={28} color={colors.blue600} /></View><Text variant="headlineSmall" style={styles.gymName}>{session.gym_name ?? '암장 정보 없음'}</Text></View>
      <View style={styles.detailGrid}>{detailItems.map((item) => <View key={item.label} style={styles.detailItem}><Icon source={item.icon} size={19} color={colors.textMuted} /><View style={styles.detailText}><Text variant="labelMedium" style={uiStyles.muted}>{item.label}</Text><Text variant="bodyMedium" style={styles.detailValue}>{item.value}</Text></View></View>)}</View>
      <View style={styles.totals}><View><Text variant="labelMedium" style={uiStyles.muted}>총 시도</Text><Text variant="headlineSmall" style={styles.totalValue}>{session.total_attempts}</Text></View><View style={styles.totalDivider} /><View><Text variant="labelMedium" style={uiStyles.muted}>총 완등</Text><Text variant="headlineSmall" style={styles.totalValue}>{session.total_sends}</Text></View></View>
      {session.notes && <View style={styles.notes}><Text variant="labelLarge">메모</Text><Text variant="bodyMedium" style={styles.notesText}>{session.notes}</Text></View>}
    </Card.Content></Card>
    <GradeLogSection sessionId={id} onChanged={handleGradeLogsChanged} />
    <SessionVideoSection sessionId={id} />
    <Button mode="outlined" icon="delete-outline" textColor={colors.error} style={uiStyles.destructiveButton} onPress={() => setDeleteDialogVisible(true)} disabled={isDeleting} contentStyle={uiStyles.primaryButton}>세션 삭제</Button>
    <ConfirmDialog visible={deleteDialogVisible} title="세션 삭제" message="이 운동 기록을 삭제할까요? 삭제한 기록은 복구할 수 없습니다." busy={isDeleting} onCancel={() => setDeleteDialogVisible(false)} onConfirm={() => void confirmDelete()} />
    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)}>{error}</Snackbar>
  </Screen>;
}

const styles = StyleSheet.create({
  heroCard: { borderRadius: radius.lg }, card: { gap: spacing.lg },
  gymHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md }, gymIcon: { width: 48, height: 48, borderRadius: radius.md, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' }, gymName: { flex: 1, color: colors.navy900, fontWeight: '800', flexShrink: 1 },
  detailGrid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: spacing.lg }, detailItem: { width: '50%', flexDirection: 'row', gap: spacing.sm, paddingRight: spacing.sm }, detailText: { flex: 1, gap: 2 }, detailValue: { color: colors.text, flexShrink: 1 },
  totals: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', borderRadius: radius.md, backgroundColor: colors.surfaceMuted, padding: spacing.lg }, totalDivider: { width: 1, height: 42, backgroundColor: colors.border }, totalValue: { color: colors.blue700, fontWeight: '800', textAlign: 'center' },
  notes: { gap: spacing.sm, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border, paddingTop: spacing.md }, notesText: { color: colors.textMuted, lineHeight: 21 },
});

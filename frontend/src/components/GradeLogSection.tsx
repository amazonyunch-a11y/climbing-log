import { gradeLogsApi } from '@/src/api/gradeLogs';
import { ApiError } from '@/src/api/client';
import { ConfirmDialog, EmptyState, LoadingState, SectionHeader, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { GradeLog } from '@/src/types/gradeLog';
import { useCallback, useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Divider, HelperText, IconButton, Snackbar, Text, TextInput, useTheme } from 'react-native-paper';

export type GradeTotals = { totalAttempts: number; totalSends: number };

type GradeLogSectionProps = { sessionId: number; onChanged: (totals?: GradeTotals) => void };

function calculateGradeTotals(grades: GradeLog[]): GradeTotals {
  return grades.reduce(
    (totals, grade) => ({
      totalAttempts: totals.totalAttempts + (grade.attempts ?? 0),
      totalSends: totals.totalSends + (grade.sends ?? 0),
    }),
    { totalAttempts: 0, totalSends: 0 },
  );
}

export function GradeLogSection({ sessionId, onChanged }: GradeLogSectionProps) {
  const theme = useTheme();
  const [grades, setGrades] = useState<GradeLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  const [editing, setEditing] = useState<GradeLog | null | undefined>(undefined);
  const [deleting, setDeleting] = useState<GradeLog>();
  const [isDeleting, setIsDeleting] = useState(false);
  const [gradeLabel, setGradeLabel] = useState('');
  const [attempts, setAttempts] = useState('0');
  const [sends, setSends] = useState('0');
  const requestId = useRef(0);

  const loadGrades = useCallback(async (): Promise<GradeLog[] | undefined> => {
    const currentRequest = ++requestId.current;
    setIsLoading(true); setGrades([]); setError(undefined);
    try {
      const response = await gradeLogsApi.list(sessionId);
      if (currentRequest === requestId.current) {
        setGrades(response);
        return response;
      }
    } catch (cause) { if (currentRequest === requestId.current) setError(cause instanceof ApiError ? cause.message : '난이도 기록을 불러오지 못했습니다.'); }
    finally { if (currentRequest === requestId.current) setIsLoading(false); }
  }, [sessionId]);

  useEffect(() => { void loadGrades(); }, [loadGrades]);

  const openAdd = () => { setEditing(null); setGradeLabel(''); setAttempts('0'); setSends('0'); setError(undefined); };
  const openEdit = (grade: GradeLog) => { setEditing(grade); setGradeLabel(grade.grade_label ?? ''); setAttempts(String(grade.attempts ?? 0)); setSends(String(grade.sends ?? 0)); setError(undefined); };
  const closeDialog = () => { if (!isSubmitting) setEditing(undefined); };

  const save = async () => {
    const parsedAttempts = Number(attempts); const parsedSends = Number(sends);
    if (!gradeLabel.trim() || !Number.isInteger(parsedAttempts) || !Number.isInteger(parsedSends) || parsedAttempts < 0 || parsedSends < 0) { setError('난이도와 0 이상의 정수 시도·완등 횟수를 입력해 주세요.'); return; }
    if (parsedSends > parsedAttempts) { setError('완등 횟수는 시도 횟수보다 클 수 없습니다.'); return; }
    setIsSubmitting(true); setError(undefined);
    try {
      const payload = { grade_label: gradeLabel.trim(), attempts: parsedAttempts, sends: parsedSends };
      if (editing) await gradeLogsApi.update(editing.id, payload); else await gradeLogsApi.create(sessionId, payload);
      setEditing(undefined); const gradesAfterSave = await loadGrades(); onChanged(gradesAfterSave && calculateGradeTotals(gradesAfterSave));
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : '난이도 기록을 저장하지 못했습니다.'); }
    finally { setIsSubmitting(false); }
  };

  const confirmRemove = async (gradeId: number) => {
    setIsDeleting(true);
    setError(undefined);
    try { await gradeLogsApi.remove(gradeId); setDeleting(undefined); const gradesAfterDelete = await loadGrades(); onChanged(gradesAfterDelete && calculateGradeTotals(gradesAfterDelete)); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '난이도 기록을 삭제하지 못했습니다.'); }
    finally { setIsDeleting(false); }
  };

  const { totalAttempts, totalSends } = calculateGradeTotals(grades);
  return <View style={styles.container}>
    <SectionHeader title="난이도 기록" description="난이도별 시도와 완등을 기록하세요." action={<Button mode="contained-tonal" icon="plus" compact onPress={openAdd}>추가</Button>} />
    {isLoading ? <LoadingState label="난이도 기록을 불러오는 중입니다." /> : grades.length === 0 ? <EmptyState title="난이도 기록이 없어요" description="첫 난이도 기록을 추가해 보세요." icon="chart-timeline-variant" /> : <Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.list}>{grades.map((grade, index) => { const attemptCount = grade.attempts ?? 0; const sendCount = grade.sends ?? 0; const rate = attemptCount === 0 ? 0 : Math.round((sendCount / attemptCount) * 100); return <View key={grade.id}><View style={styles.gradeRow}><View style={styles.gradeInfo}><View style={styles.gradeBadge}><Text variant="titleMedium" style={styles.gradeBadgeText}>{grade.grade_label ?? '-'}</Text></View><View style={styles.gradeMetrics}><Text variant="bodyMedium">시도 {attemptCount} · 완등 {sendCount}</Text><Text variant="bodySmall" style={uiStyles.muted}>성공률 {rate}%</Text></View></View><View style={styles.actions}><IconButton icon="pencil-outline" accessibilityLabel="난이도 기록 수정" onPress={() => openEdit(grade)} /><IconButton icon="delete-outline" iconColor={colors.error} accessibilityLabel="난이도 기록 삭제" onPress={() => setDeleting(grade)} /></View></View>{index < grades.length - 1 && <Divider />}</View>; })}</Card.Content></Card>}
    {!isLoading && grades.length > 0 && <View style={styles.totals}><Text variant="labelLarge">합계</Text><Text variant="bodyMedium">시도 <Text style={styles.totalNumber}>{totalAttempts}</Text></Text><Text variant="bodyMedium">완등 <Text style={styles.totalNumber}>{totalSends}</Text></Text></View>}
    <Modal transparent visible={editing !== undefined} animationType="fade" onRequestClose={closeDialog}><KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalRoot}><Pressable style={styles.backdrop} onPress={closeDialog} disabled={isSubmitting} /><View style={[styles.sheet, { backgroundColor: theme.colors.surface }]}><View style={styles.sheetHandle} /><Text variant="titleLarge" style={styles.sheetTitle}>{editing ? '난이도 기록 수정' : '난이도 기록 추가'}</Text><Text variant="bodySmall" style={uiStyles.muted}>시도와 완등 횟수는 0 이상의 정수로 입력해 주세요.</Text><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.sheetInputs}><TextInput label="난이도" value={gradeLabel} onChangeText={setGradeLabel} mode="outlined" style={uiStyles.input} placeholder="예: V3" autoFocus /><View style={styles.numberFields}><TextInput label="시도 횟수" value={attempts} onChangeText={setAttempts} mode="outlined" style={[uiStyles.input, styles.numberField]} keyboardType="number-pad" /><TextInput label="완등 횟수" value={sends} onChangeText={setSends} mode="outlined" style={[uiStyles.input, styles.numberField]} keyboardType="number-pad" /></View><HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText></ScrollView><View style={styles.sheetActions}><Button mode="text" onPress={closeDialog} disabled={isSubmitting}>취소</Button><Button mode="contained" onPress={save} loading={isSubmitting} disabled={isSubmitting} contentStyle={uiStyles.primaryButton}>저장</Button></View></View></KeyboardAvoidingView></Modal>
    <ConfirmDialog visible={Boolean(deleting)} title="난이도 기록 삭제" message={`${deleting?.grade_label ?? '이 기록'}을 삭제할까요?`} busy={isDeleting} onCancel={() => setDeleting(undefined)} onConfirm={() => deleting && void confirmRemove(deleting.id)} />
    <Snackbar visible={Boolean(error) && editing === undefined} onDismiss={() => setError(undefined)} action={{ label: '다시 시도', onPress: () => void loadGrades() }}>{error}</Snackbar>
  </View>;
}

const styles = StyleSheet.create({
  container: { gap: spacing.md }, list: { gap: spacing.sm }, gradeRow: { minHeight: 66, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: spacing.xs },
  gradeInfo: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: spacing.md }, gradeBadge: { minWidth: 48, minHeight: 42, paddingHorizontal: spacing.sm, borderRadius: radius.md, backgroundColor: colors.blue100, alignItems: 'center', justifyContent: 'center' }, gradeBadgeText: { color: colors.navy900, fontWeight: '800' }, gradeMetrics: { flex: 1, gap: 2 }, actions: { flexDirection: 'row' },
  totals: { flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: spacing.lg, paddingHorizontal: spacing.md }, totalNumber: { color: colors.blue700, fontWeight: '800' },
  modalRoot: { flex: 1, justifyContent: 'flex-end' }, backdrop: { ...StyleSheet.absoluteFill, backgroundColor: colors.scrim },
  sheet: { maxHeight: '82%', borderTopLeftRadius: radius.xl, borderTopRightRadius: radius.xl, paddingTop: spacing.sm, paddingHorizontal: spacing.xl, paddingBottom: spacing.xxl, gap: spacing.sm }, sheetHandle: { width: 42, height: 4, borderRadius: 2, backgroundColor: colors.border, alignSelf: 'center', marginBottom: spacing.sm }, sheetTitle: { color: colors.navy900, fontWeight: '700' },
  sheetInputs: { gap: spacing.md, paddingBottom: spacing.sm }, numberFields: { flexDirection: 'row', gap: spacing.sm }, numberField: { flex: 1 }, sheetActions: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', gap: spacing.sm, paddingTop: spacing.xs },
});

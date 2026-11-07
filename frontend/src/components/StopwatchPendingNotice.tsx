import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Icon, Text, TouchableRipple } from 'react-native-paper';

import { colors, radius, spacing } from '@/src/constants/theme';
import type { Stopwatch } from '@/src/types/stopwatch';
import { formatKstTimeSeconds } from '@/src/utils/date';

function formatElapsed(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return [hours, minutes, remainingSeconds].map((value) => String(value).padStart(2, '0')).join(':');
}

type Props = {
  stopwatches: Stopwatch[];
  action?: ReactNode;
  selectedStopwatchId?: number | null;
  onSelect?: (stopwatch: Stopwatch) => void;
  onClearSelection?: () => void;
  autoSelected?: boolean;
};

export function StopwatchPendingNotice({
  stopwatches,
  action,
  selectedStopwatchId,
  onSelect,
  onClearSelection,
  autoSelected = false,
}: Props) {
  if (stopwatches.length === 0) return null;
  const isSelectable = Boolean(onSelect);
  const description = isSelectable
    ? stopwatches.length === 1
      ? selectedStopwatchId == null
        ? '세션에 연결할 운동 시간을 선택해 주세요.'
        : autoSelected
          ? '저장된 운동 시간 1건을 자동 선택했습니다.'
          : '저장된 운동 시간 1건을 선택했습니다.'
      : '세션에 연결할 운동 시간 한 건을 선택해 주세요.'
    : '세션을 추가하면 연결할 수 있습니다.';

  return <Card mode="outlined" style={styles.card}>
    <Card.Content style={styles.content}>
      <View style={styles.header}>
        <View style={styles.icon}><Icon source="timer-check-outline" size={22} color={colors.blue700} /></View>
        <View style={styles.headerText}>
          <Text variant="titleMedium" style={styles.title}>{isSelectable ? '저장된 운동 시간 선택' : '저장된 운동 시간'}</Text>
          <Text variant="bodySmall" style={styles.description}>{description}</Text>
        </View>
      </View>
      <View accessibilityRole={isSelectable ? 'radiogroup' : undefined} style={styles.records}>
        {stopwatches.map((stopwatch) => {
          const selected = stopwatch.id === selectedStopwatchId;
          const record = <View style={[styles.record, selected && styles.recordSelected]}>
            <View style={styles.recordHeader}>
              <View style={styles.recordText}>
                <Text variant="titleLarge" style={[styles.duration, selected && styles.durationSelected]}>{formatElapsed(stopwatch.elapsedSeconds)}</Text>
                <Text variant="bodySmall" style={[styles.description, selected && styles.descriptionSelected]}>
                  시작 {formatKstTimeSeconds(stopwatch.startedAt)} · 종료 {stopwatch.endedAt ? formatKstTimeSeconds(stopwatch.endedAt) : '없음'}
                </Text>
              </View>
              {selected && <Icon source="check-circle" size={24} color={colors.blue700} />}
            </View>
            {selected && autoSelected && <Text variant="labelSmall" style={styles.autoLabel}>자동으로 선택된 기록입니다.</Text>}
          </View>;

          if (!isSelectable) return <View key={stopwatch.id}>{record}</View>;
          return <TouchableRipple
            key={stopwatch.id}
            onPress={() => onSelect?.(stopwatch)}
            accessibilityRole="radio"
            accessibilityState={{ checked: selected }}
            style={styles.ripple}
            borderless={false}
          >
            {record}
          </TouchableRipple>;
        })}
      </View>
      {isSelectable && selectedStopwatchId != null && onClearSelection && <Button mode="text" icon="close-circle-outline" onPress={onClearSelection} style={styles.clearButton}>선택 해제</Button>}
      {action}
    </Card.Content>
  </Card>;
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#EEF4F9', borderColor: colors.border, borderRadius: radius.lg },
  content: { gap: spacing.md },
  header: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  icon: { width: 38, height: 38, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.blue100 },
  headerText: { flex: 1, gap: 2 },
  title: { color: colors.navy900, fontWeight: '700' },
  description: { color: colors.textMuted, flexShrink: 1 },
  records: { gap: spacing.sm },
  ripple: { borderRadius: radius.md },
  record: { gap: spacing.xs, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, padding: spacing.md },
  recordSelected: { borderColor: colors.blue600, backgroundColor: colors.blue100 },
  recordHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  recordText: { flex: 1, gap: 2 },
  duration: { color: colors.blue700, fontWeight: '800', fontVariant: ['tabular-nums'] },
  durationSelected: { color: colors.navy900 },
  descriptionSelected: { color: colors.navy800 },
  autoLabel: { color: colors.blue700, fontWeight: '700' },
  clearButton: { alignSelf: 'flex-start' },
});

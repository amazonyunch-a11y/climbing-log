import DateTimePicker from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { Button, Text } from 'react-native-paper';
import { createKstPickerDate, formatKstTime } from '@/src/utils/date';
import { colors, radius, spacing } from '@/src/constants/theme';

type Props = {
  label: string;
  sessionDate: string;
  value?: string;
  emptyLabel?: string;
  clearable?: boolean;
  onChange: (value?: string) => void;
};

export function SessionTimePicker({ label, sessionDate, value, emptyLabel = '시간을 선택하세요', clearable = false, onChange }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const pickerValue = createKstPickerDate(sessionDate, value ?? '18:00');

  return <View style={styles.field}>
    <Text variant="labelLarge">{label}</Text>
    <Button mode="outlined" icon="clock-outline" onPress={() => setIsOpen(true)} contentStyle={styles.buttonContent} style={styles.button}>
      {value ?? emptyLabel}
    </Button>
    {isOpen && <View style={styles.picker}>
      <DateTimePicker
        value={pickerValue}
        mode="time"
        display={Platform.OS === 'ios' ? 'spinner' : 'default'}
        is24Hour
        timeZoneName="Asia/Seoul"
        onChange={(_, selectedDate) => {
          if (Platform.OS !== 'ios') setIsOpen(false);
          if (selectedDate) onChange(formatKstTime(selectedDate));
        }}
      />
      {Platform.OS === 'ios' && <Button mode="contained-tonal" onPress={() => setIsOpen(false)}>완료</Button>}
    </View>}
    {clearable && value && <Button mode="text" onPress={() => onChange(undefined)} style={styles.clearButton}>종료 시간 지우기</Button>}
  </View>;
}

const styles = StyleSheet.create({
  field: { gap: spacing.sm },
  button: { borderColor: colors.border, backgroundColor: colors.surface },
  buttonContent: { minHeight: 48, justifyContent: 'flex-start' },
  picker: { borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border, borderRadius: radius.md, overflow: 'hidden', padding: spacing.sm, backgroundColor: colors.surface },
  clearButton: { alignSelf: 'flex-start' },
});

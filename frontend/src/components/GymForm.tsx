import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, HelperText, TextInput } from 'react-native-paper';
import { uiStyles } from '@/src/components/ui';
import { spacing } from '@/src/constants/theme';

type GymFormProps = {
  initialName?: string;
  initialLocation?: string;
  submitLabel: string;
  isSubmitting: boolean;
  error?: string;
  onSubmit: (values: { name: string; location: string }) => Promise<void>;
};

export function GymForm({
  initialName = '',
  initialLocation = '',
  submitLabel,
  isSubmitting,
  error,
  onSubmit,
}: GymFormProps) {
  const [name, setName] = useState(initialName);
  const [location, setLocation] = useState(initialLocation);
  const [validationError, setValidationError] = useState<string>();

  const submit = async () => {
    const trimmedName = name.trim();
    const trimmedLocation = location.trim();
    if (!trimmedName || !trimmedLocation) {
      setValidationError('암장 이름과 위치를 모두 입력해 주세요.');
      return;
    }

    setValidationError(undefined);
    await onSubmit({ name: trimmedName, location: trimmedLocation });
  };

  return <View style={styles.form}>
    <TextInput label="암장 이름" value={name} onChangeText={setName} mode="outlined" style={uiStyles.input} autoFocus />
    <TextInput label="주소 또는 위치" value={location} onChangeText={setLocation} mode="outlined" style={uiStyles.input} multiline onSubmitEditing={submit} />
    <HelperText type="error" visible={Boolean(validationError || error)}>{validationError || error || ' '}</HelperText>
    <Button mode="contained" onPress={submit} loading={isSubmitting} disabled={isSubmitting} contentStyle={uiStyles.primaryButton}>{submitLabel}</Button>
  </View>;
}

const styles = StyleSheet.create({ form: { gap: spacing.md } });

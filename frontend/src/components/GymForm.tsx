import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, HelperText, Text, TextInput } from 'react-native-paper';
import { KakaoPlacePicker, type KakaoPlaceSelection } from '@/src/components/KakaoPlacePicker';
import { uiStyles } from '@/src/components/ui';
import { spacing } from '@/src/constants/theme';

type GymFormProps = {
  initialName?: string;
  initialLocation?: string;
  submitLabel: string;
  isSubmitting: boolean;
  error?: string;
  enablePlacePicker?: boolean;
  onSubmit: (values: { name: string; location: string }) => Promise<void>;
};

export function GymForm({
  initialName = '',
  initialLocation = '',
  submitLabel,
  isSubmitting,
  error,
  enablePlacePicker = false,
  onSubmit,
}: GymFormProps) {
  const [name, setName] = useState(initialName);
  const [location, setLocation] = useState(initialLocation);
  const [validationError, setValidationError] = useState<string>();
  const [placePickerVisible, setPlacePickerVisible] = useState(false);

  const selectPlace = (place: KakaoPlaceSelection) => {
    setName(place.placeName);
    setLocation(place.roadAddressName || place.addressName);
    setValidationError(undefined);
  };

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
    {enablePlacePicker && <View style={styles.placeSearch}>
      <Button mode="outlined" icon="map-search-outline" onPress={() => setPlacePickerVisible(true)} disabled={isSubmitting} contentStyle={uiStyles.primaryButton}>지도에서 암장 찾기</Button>
      <Text variant="bodySmall" style={uiStyles.muted}>직접 입력하거나 카카오 장소 검색 결과를 선택할 수 있습니다.</Text>
    </View>}
    <HelperText type="error" visible={Boolean(validationError || error)}>{validationError || error || ' '}</HelperText>
    <Button mode="contained" onPress={submit} loading={isSubmitting} disabled={isSubmitting} contentStyle={uiStyles.primaryButton}>{submitLabel}</Button>
    {enablePlacePicker && <KakaoPlacePicker visible={placePickerVisible} onDismiss={() => setPlacePickerVisible(false)} onSelect={selectPlace} />}
  </View>;
}

const styles = StyleSheet.create({ form: { gap: spacing.md }, placeSearch: { gap: spacing.xs } });

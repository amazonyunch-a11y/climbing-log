import DateTimePicker from '@react-native-community/datetimepicker';
import { ApiError } from '@/src/api/client';
import { useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import { Avatar, Button, Card, Divider, HelperText, Icon, Snackbar, Text, TextInput } from 'react-native-paper';

import { profileApi } from '@/src/api/profile';
import { useAuth } from '@/src/auth/AuthProvider';
import { ErrorState, LoadingState, PageHeader, Screen, SectionHeader, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { Profile, ProfileUpdate } from '@/src/types/profile';
import { formatKstDate, formatLocalDate, parseLocalDate } from '@/src/utils/date';
import { nicknameApiError, normalizeNickname, validateNickname } from '@/src/utils/nickname';

type Form = { birthDate: string; heightCm: string; weightKg: string; armLengthCm: string };
type NumberKey = 'heightCm' | 'weightKg' | 'armLengthCm';

const numberFields: { key: NumberKey; label: string; unit: string; min: number; max: number }[] = [
  { key: 'heightCm', label: '키', unit: 'cm', min: 50, max: 250 },
  { key: 'weightKg', label: '몸무게', unit: 'kg', min: 10, max: 300 },
  { key: 'armLengthCm', label: '팔 리치', unit: 'cm', min: 50, max: 300 },
];

function toForm(profile: Profile): Form {
  return {
    birthDate: profile.birth_date ?? '',
    heightCm: profile.height_cm?.toString() ?? '',
    weightKg: profile.weight_kg?.toString() ?? '',
    armLengthCm: profile.arm_length_cm?.toString() ?? '',
  };
}

function validate(form: Form, today: string): Partial<Record<keyof Form, string>> {
  const errors: Partial<Record<keyof Form, string>> = {};
  if (form.birthDate) {
    const date = parseLocalDate(form.birthDate);
    if (Number.isNaN(date.getTime()) || formatLocalDate(date) !== form.birthDate || form.birthDate > today) {
      errors.birthDate = '오늘 이전의 올바른 생년월일을 선택해 주세요.';
    }
  }
  for (const field of numberFields) {
    const value = form[field.key].trim();
    if (value && (!/^\d+$/.test(value) || Number(value) < field.min || Number(value) > field.max)) {
      errors[field.key] = `${field.min}~${field.max}${field.unit} 사이의 정수를 입력해 주세요.`;
    }
  }
  return errors;
}

export default function ProfileScreen() {
  const { user, logout, refreshUser } = useAuth();
  const requestId = useRef(0);
  const nicknameSubmitting = useRef(false);
  const [nicknameInput, setNicknameInput] = useState('');
  const [originalNickname, setOriginalNickname] = useState<string>();
  const [nicknameSaving, setNicknameSaving] = useState(false);
  const [nicknameAttempted, setNicknameAttempted] = useState(false);
  const [nicknameError, setNicknameError] = useState<string>();
  const [form, setForm] = useState<Form>();
  const [original, setOriginal] = useState<Form>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [loadError, setLoadError] = useState<string>();
  const [saveError, setSaveError] = useState<string>();
  const [successMessage, setSuccessMessage] = useState<string>();
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof Form, string>>>({});
  const [dateOpen, setDateOpen] = useState(false);
  const [draftDate, setDraftDate] = useState(new Date());

  const loadProfile = useCallback(async () => {
    const current = ++requestId.current;
    setLoading(true);
    setLoadError(undefined);
    try {
      const profile = await profileApi.get();
      const values = toForm(profile);
      if (current !== requestId.current) return;
      setNicknameInput(profile.nickname ?? '');
      setOriginalNickname(profile.nickname ?? '');
      setNicknameAttempted(false);
      setNicknameError(undefined);
      setForm(values);
      setOriginal(values);
      setFieldErrors({});
    } catch (cause) {
      if (current === requestId.current) setLoadError(cause instanceof ApiError ? `프로필 조회 실패: ${cause.message}` : '프로필 정보를 불러오지 못했습니다. 다시 시도해 주세요.');
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => {
    void loadProfile();
    return () => { requestId.current += 1; };
  }, [loadProfile]));

  const updateField = (key: keyof Form, value: string) => {
    setForm((current) => current ? { ...current, [key]: value } : current);
    setFieldErrors((current) => ({ ...current, [key]: undefined }));
    setSaveError(undefined);
    setSuccessMessage(undefined);
  };

  const today = formatKstDate(new Date());
  const maximumDate = parseLocalDate(today);
  const openDate = () => {
    setDraftDate(form?.birthDate ? parseLocalDate(form.birthDate) : maximumDate);
    setDateOpen(true);
  };

  const saveNickname = async () => {
    if (nicknameSubmitting.current || saving || originalNickname === undefined) return;
    setNicknameAttempted(true);
    if (validateNickname(nicknameInput)) return;
    const normalized = normalizeNickname(nicknameInput);
    if (normalized === originalNickname) return;
    nicknameSubmitting.current = true;
    setNicknameSaving(true);
    setNicknameError(undefined);
    try {
      const saved = await profileApi.update({ nickname: normalized });
      setNicknameInput(saved.nickname ?? normalized);
      setOriginalNickname(saved.nickname ?? normalized);
      setNicknameAttempted(false);
      try {
        await refreshUser();
        setSuccessMessage('닉네임을 변경했습니다.');
      } catch {
        setNicknameError('닉네임은 저장되었지만 계정 정보를 새로 불러오지 못했습니다. 다시 진입해 확인해 주세요.');
      }
    } catch (cause) {
      setNicknameError(cause instanceof ApiError ? nicknameApiError(cause.message, cause.status) : '닉네임을 저장하지 못했습니다. 다시 시도해 주세요.');
    } finally {
      nicknameSubmitting.current = false;
      setNicknameSaving(false);
    }
  };

  const save = async () => {
    if (!form || !original || saving || nicknameSaving) return;
    const errors = validate(form, today);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    const payload: ProfileUpdate = {};
    if (form.birthDate !== original.birthDate) payload.birth_date = form.birthDate || null;
    if (form.heightCm !== original.heightCm) payload.height_cm = form.heightCm ? Number(form.heightCm) : null;
    if (form.weightKg !== original.weightKg) payload.weight_kg = form.weightKg ? Number(form.weightKg) : null;
    if (form.armLengthCm !== original.armLengthCm) payload.arm_length_cm = form.armLengthCm ? Number(form.armLengthCm) : null;
    if (Object.keys(payload).length === 0) return;
    setSaving(true);
    setSaveError(undefined);
    try {
      const saved = toForm(await profileApi.update(payload));
      setForm(saved);
      setOriginal(saved);
      setSuccessMessage('신체 정보를 저장했습니다.');
    } catch (cause) {
      setSaveError(cause instanceof ApiError ? `저장 실패: ${cause.message}` : '신체 정보를 저장하지 못했습니다. 다시 시도해 주세요.');
    } finally {
      setSaving(false);
    }
  };

  const onLogout = async () => {
    setIsLoggingOut(true);
    try { await logout(); } finally { setIsLoggingOut(false); }
  };

  if (!user) return <Screen><LoadingState label="프로필을 불러오는 중입니다." /></Screen>;

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.screenContent}>
      <PageHeader title="프로필" subtitle="계정 정보와 신체 정보를 관리하세요." />
      <Card mode="outlined" style={[uiStyles.card, styles.profileCard]}><Card.Content style={styles.cardContent}>
        <Avatar.Text size={72} label={(originalNickname ?? user.nickname ?? 'U').slice(0, 1).toUpperCase()} style={styles.avatar} labelStyle={styles.avatarLabel} />
        <View style={styles.identity}><Text variant="headlineSmall" style={styles.nickname}>{originalNickname ?? user.nickname}</Text><Text variant="bodyMedium" style={uiStyles.muted}>{user.email}</Text></View>
        <Divider />
        <View style={styles.infoRow}><View style={styles.infoIcon}><Icon source="account-outline" size={21} color={colors.blue600} /></View><View style={styles.infoText}><Text variant="labelMedium" style={uiStyles.muted}>닉네임</Text><Text variant="bodyLarge">{originalNickname ?? user.nickname}</Text></View></View>
        <View style={styles.infoRow}><View style={styles.infoIcon}><Icon source="email-outline" size={21} color={colors.blue600} /></View><View style={styles.infoText}><Text variant="labelMedium" style={uiStyles.muted}>이메일</Text><Text variant="bodyLarge" numberOfLines={2}>{user.email}</Text></View></View>
        {originalNickname !== undefined && <>
          <Divider />
          <TextInput label="닉네임 변경" value={nicknameInput} onChangeText={(value) => { setNicknameInput(value); setNicknameError(undefined); }} autoCapitalize="none" autoCorrect={false} mode="outlined" style={uiStyles.input} error={Boolean(nicknameAttempted && validateNickname(nicknameInput))} disabled={nicknameSaving} />
          <Text variant="bodySmall" style={uiStyles.muted}>영문 대·소문자를 각각 1개 이상 포함한 5~15자의 영문·숫자</Text>
          <HelperText type="error" visible={Boolean(nicknameAttempted && validateNickname(nicknameInput))}>{nicknameAttempted ? validateNickname(nicknameInput) : ' '}</HelperText>
          {nicknameError && <Text variant="bodyMedium" style={styles.errorText}>{nicknameError}</Text>}
          <Button mode="contained-tonal" onPress={() => void saveNickname()} loading={nicknameSaving} disabled={nicknameSaving || saving || normalizeNickname(nicknameInput) === originalNickname} contentStyle={uiStyles.primaryButton}>닉네임 저장</Button>
        </>}
      </Card.Content></Card>

      <SectionHeader title="신체 정보" description="입력한 정보는 언제든 수정하거나 지울 수 있습니다." />
      {loading ? <LoadingState label="신체 정보를 불러오는 중입니다." /> : loadError ? <ErrorState message={loadError} onRetry={() => void loadProfile()} /> : form && original ?
        <Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.formContent}>
          <View style={styles.field}>
            <Text variant="labelLarge">생년월일</Text>
            <Button mode="outlined" icon="calendar" onPress={openDate} style={styles.dateButton} contentStyle={styles.dateButtonContent} disabled={saving}>
              {form.birthDate ? form.birthDate.replace(/-/g, '.') : '생년월일 선택'}
            </Button>
            {dateOpen && Platform.OS === 'ios' && <View style={styles.datePicker}>
              <DateTimePicker value={draftDate} mode="date" display="spinner" maximumDate={maximumDate} onChange={(_, selected) => { if (selected) setDraftDate(selected); }} />
              <View style={styles.dateActions}>
                <Button onPress={() => setDateOpen(false)}>취소</Button>
                <Button mode="contained-tonal" onPress={() => { updateField('birthDate', formatLocalDate(draftDate)); setDateOpen(false); }}>선택 완료</Button>
              </View>
            </View>}
            {dateOpen && Platform.OS !== 'ios' && <DateTimePicker value={draftDate} mode="date" display="default" maximumDate={maximumDate} onChange={(event, selected) => {
              setDateOpen(false);
              if (event.type === 'set' && selected) updateField('birthDate', formatLocalDate(selected));
            }} />}
            {form.birthDate && <Button mode="text" onPress={() => updateField('birthDate', '')} style={styles.clearButton} disabled={saving}>생년월일 지우기</Button>}
            <HelperText type="error" visible={Boolean(fieldErrors.birthDate)}>{fieldErrors.birthDate ?? ' '}</HelperText>
          </View>

          {numberFields.map((field) => <View key={field.key} style={styles.field}>
            <TextInput label={field.label} value={form[field.key]} onChangeText={(value) => updateField(field.key, value)} mode="outlined" style={uiStyles.input} keyboardType="number-pad" maxLength={3} right={<TextInput.Affix text={field.unit} />} error={Boolean(fieldErrors[field.key])} disabled={saving} />
            {field.key === 'armLengthCm' && <Text variant="bodySmall" style={uiStyles.muted}>양팔을 좌우로 벌렸을 때의 전체 길이입니다.</Text>}
            <HelperText type="error" visible={Boolean(fieldErrors[field.key])}>{fieldErrors[field.key] ?? ' '}</HelperText>
          </View>)}
          <Button mode="contained" onPress={() => void save()} loading={saving} disabled={saving || nicknameSaving || isLoggingOut || JSON.stringify(form) === JSON.stringify(original)} contentStyle={uiStyles.primaryButton}>신체 정보 저장</Button>
          {saveError && <Text variant="bodyMedium" style={styles.errorText}>{saveError}</Text>}
        </Card.Content></Card> : null}

      <Button mode="outlined" icon="logout" textColor={colors.error} style={uiStyles.destructiveButton} onPress={onLogout} loading={isLoggingOut} disabled={isLoggingOut || saving || nicknameSaving} contentStyle={uiStyles.primaryButton}>로그아웃</Button>
    </Screen>
    <Snackbar visible={Boolean(successMessage)} onDismiss={() => setSuccessMessage(undefined)} duration={3000}>{successMessage}</Snackbar>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  root: { flex: 1 }, screenContent: { paddingBottom: spacing.xxxl * 2 },
  profileCard: { borderRadius: radius.lg }, cardContent: { gap: spacing.lg, paddingVertical: spacing.lg },
  avatar: { alignSelf: 'center', backgroundColor: colors.navy900 }, avatarLabel: { color: '#FFFFFF', fontWeight: '800' },
  identity: { alignItems: 'center', gap: spacing.xs }, nickname: { color: colors.navy900, fontWeight: '800' },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  infoIcon: { width: 42, height: 42, borderRadius: radius.md, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' },
  infoText: { flex: 1, gap: 2 }, formContent: { gap: spacing.sm, paddingVertical: spacing.lg }, field: { minWidth: 0 },
  dateButton: { borderColor: colors.border, backgroundColor: colors.surface },
  dateButtonContent: { minHeight: 48, justifyContent: 'flex-start' },
  datePicker: { borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border, borderRadius: radius.md, overflow: 'hidden', backgroundColor: colors.surface },
  dateActions: { flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.sm },
  clearButton: { alignSelf: 'flex-start' }, errorText: { color: colors.error },
});

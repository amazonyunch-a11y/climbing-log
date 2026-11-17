import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Button, Card, HelperText, Text, TextInput } from 'react-native-paper';
import { Screen, PageHeader, uiStyles } from '@/src/components/ui';
import { radius, spacing } from '@/src/constants/theme';
import { nicknameApiError, normalizeNickname, validateNickname } from '@/src/utils/nickname';

export default function SignupScreen() {
  const { signup } = useAuth();
  const router = useRouter();
  const [nickname, setNickname] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [validationAttempted, setValidationAttempted] = useState(false);
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);

  const confirmError = validationAttempted && password
    ? !passwordConfirm
      ? '비밀번호 확인을 입력해 주세요.'
      : password !== passwordConfirm
        ? '비밀번호가 일치하지 않습니다.'
        : undefined
    : undefined;
  const nicknameError = validationAttempted && nickname.trim() ? validateNickname(nickname) : undefined;

  const submit = async () => {
    if (submittingRef.current) return;
    setValidationAttempted(true);
    if (!nickname.trim() || !email.trim() || !password) {
      setError('닉네임, 이메일, 비밀번호를 모두 입력해 주세요.');
      return;
    }
    setError(undefined);
    if (validateNickname(nickname)) return;
    if (!passwordConfirm || password !== passwordConfirm) return;
    submittingRef.current = true;
    setSubmitting(true);
    try {
      const createdUser = await signup({ nickname: normalizeNickname(nickname), email: email.trim(), password });
      setNickname('');
      setEmail('');
      setPassword('');
      setPasswordConfirm('');
      setShowPassword(false);
      setShowPasswordConfirm(false);
      setValidationAttempted(false);
      router.replace({ pathname: '/email-verification', params: { email: createdUser.email, autoRequest: '1' } });
    } catch (cause) {
      setError(cause instanceof ApiError ? nicknameApiError(cause.message, cause.status) : '회원가입에 실패했습니다.');
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.container}>
      <PageHeader title="계정 만들기" subtitle="기록을 안전하게 보관할 계정을 만들어 주세요." onBack={() => router.back()} />
      <Card mode="outlined" style={[uiStyles.card, styles.card]}><Card.Content style={styles.form}>
        <TextInput label="닉네임" value={nickname} onChangeText={(value) => { setNickname(value); setError(undefined); }} autoComplete="username" autoCapitalize="none" mode="outlined" style={uiStyles.input} error={Boolean(nicknameError)} />
        <HelperText type="error" visible={Boolean(nicknameError)}>{nicknameError ?? ' '}</HelperText>
        <TextInput label="이메일" value={email} onChangeText={(value) => { setEmail(value); setError(undefined); }} autoCapitalize="none" autoComplete="email" keyboardType="email-address" mode="outlined" style={uiStyles.input} />
        <TextInput label="비밀번호" placeholder="비밀번호를 입력해 주세요" value={password} onChangeText={(value) => { setPassword(value); setError(undefined); }} secureTextEntry={!showPassword} autoComplete="new-password" mode="outlined" style={uiStyles.input} right={<TextInput.Icon icon={showPassword ? 'eye-off' : 'eye'} onPress={() => setShowPassword((visible) => !visible)} accessibilityLabel={showPassword ? '비밀번호 숨기기' : '비밀번호 표시'} />} />
        <TextInput label="비밀번호 확인" placeholder="비밀번호를 다시 입력해 주세요" value={passwordConfirm} onChangeText={(value) => { setPasswordConfirm(value); setError(undefined); }} secureTextEntry={!showPasswordConfirm} autoComplete="new-password" mode="outlined" style={uiStyles.input} right={<TextInput.Icon icon={showPasswordConfirm ? 'eye-off' : 'eye'} onPress={() => setShowPasswordConfirm((visible) => !visible)} accessibilityLabel={showPasswordConfirm ? '비밀번호 확인 숨기기' : '비밀번호 확인 표시'} />} error={Boolean(confirmError)} onSubmitEditing={() => void submit()} />
        <HelperText type="error" visible={Boolean(confirmError)}>{confirmError ?? ' '}</HelperText>
        <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
        <Button mode="contained" onPress={submit} loading={submitting} disabled={submitting} contentStyle={uiStyles.primaryButton}>회원가입</Button>
        <Button mode="text" onPress={() => router.back()} disabled={submitting}>이미 계정이 있어요</Button>
      </Card.Content></Card>
    </Screen>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({ root: { flex: 1 }, container: { justifyContent: 'center', paddingVertical: spacing.xxxl }, card: { borderRadius: radius.lg }, form: { gap: spacing.md, paddingVertical: spacing.sm } });

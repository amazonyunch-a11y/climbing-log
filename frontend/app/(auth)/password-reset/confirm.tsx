import { authApi } from '@/src/api/auth';
import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Button, Card, HelperText, Text, TextInput } from 'react-native-paper';

const DELIVERY_NOTICE = '입력한 이메일이 가입된 계정이라면 인증번호를 발송했습니다.\n메일이 도착하지 않으면 가입할 때 사용한 이메일 주소인지 확인해 주세요.';

function confirmErrorMessage(cause: unknown): string {
  if (!(cause instanceof ApiError)) return '비밀번호 변경을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status === 0) return '네트워크 연결을 확인한 후 다시 시도해 주세요.';
  if (cause.status === 400) return '인증번호가 올바르지 않거나 만료되었습니다.';
  if (cause.status === 422) return '비밀번호는 8자 이상이어야 합니다.';
  if (cause.status === 429) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status >= 500) return '서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  return '비밀번호 변경을 처리하지 못했습니다. 입력값을 확인해 주세요.';
}

function resendErrorMessage(cause: unknown): string {
  if (cause instanceof ApiError && cause.status === 0) return '네트워크 연결을 확인한 후 다시 시도해 주세요.';
  if (cause instanceof ApiError && cause.status === 429) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
  return '인증번호를 다시 요청하지 못했습니다. 잠시 후 다시 시도해 주세요.';
}

export default function PasswordResetConfirmScreen() {
  const router = useRouter();
  const { resetSession } = useAuth();
  const params = useLocalSearchParams<{ email?: string }>();
  const email = typeof params.email === 'string' ? params.email.trim() : '';
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [error, setError] = useState<string>();
  const [resendMessage, setResendMessage] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const submittingRef = useRef(false);
  const resendingRef = useRef(false);

  const editEmail = () => {
    setCode('');
    setPassword('');
    setPasswordConfirm('');
    router.replace({ pathname: '/password-reset', params: email ? { email } : {} });
  };

  const submit = async () => {
    if (submittingRef.current || resendingRef.current) return;
    if (!email) {
      setError('이메일을 다시 입력해 주세요.');
      return;
    }
    if (!code) {
      setError('인증번호를 입력해 주세요.');
      return;
    }
    if (code.length !== 6) {
      setError('인증번호 6자리를 입력해 주세요.');
      return;
    }
    if (!password) {
      setError('새 비밀번호를 입력해 주세요.');
      return;
    }
    if (password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (!passwordConfirm) {
      setError('비밀번호 확인을 입력해 주세요.');
      return;
    }
    if (password !== passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError(undefined);
    setResendMessage(undefined);
    try {
      await authApi.confirmPasswordReset({
        email,
        code,
        new_password: password,
        new_password_confirm: passwordConfirm,
      });
      setCode('');
      setPassword('');
      setPasswordConfirm('');
      await resetSession();
      router.dismissTo({ pathname: '/login', params: { passwordReset: 'success' } });
    } catch (cause) {
      setError(confirmErrorMessage(cause));
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const resend = async () => {
    if (!email || submittingRef.current || resendingRef.current) return;
    resendingRef.current = true;
    setResending(true);
    setError(undefined);
    setResendMessage(undefined);
    try {
      await authApi.requestPasswordReset({ email });
      setCode('');
      setResendMessage('인증번호를 다시 요청했습니다.');
    } catch (cause) {
      setError(resendErrorMessage(cause));
    } finally {
      resendingRef.current = false;
      setResending(false);
    }
  };

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.container}>
      <PageHeader title="인증번호 확인" subtitle="인증번호를 확인한 후 새 비밀번호를 설정해 주세요." onBack={editEmail} />
      <Card mode="contained" style={styles.noticeCard}><Card.Content style={styles.noticeContent}>
        <Text variant="bodyMedium" style={styles.noticeText}>{DELIVERY_NOTICE}</Text>
        {email && <Text variant="labelLarge" style={styles.emailText}>{email}</Text>}
      </Card.Content></Card>
      <Card mode="outlined" style={[uiStyles.card, styles.card]}><Card.Content style={styles.form}>
        <TextInput
          label="인증번호"
          value={code}
          onChangeText={(value) => { setCode(value.replace(/\D/g, '').slice(0, 6)); setError(undefined); }}
          keyboardType="number-pad"
          maxLength={6}
          mode="outlined"
          style={uiStyles.input}
          disabled={submitting || resending}
        />
        <TextInput
          label="새 비밀번호"
          value={password}
          onChangeText={(value) => { setPassword(value); setError(undefined); }}
          secureTextEntry={!showPassword}
          autoComplete="new-password"
          mode="outlined"
          style={uiStyles.input}
          disabled={submitting || resending}
          right={<TextInput.Icon icon={showPassword ? 'eye-off' : 'eye'} onPress={() => setShowPassword((visible) => !visible)} accessibilityLabel={showPassword ? '비밀번호 숨기기' : '비밀번호 표시'} />}
        />
        <TextInput
          label="새 비밀번호 확인"
          value={passwordConfirm}
          onChangeText={(value) => { setPasswordConfirm(value); setError(undefined); }}
          secureTextEntry={!showPasswordConfirm}
          autoComplete="new-password"
          mode="outlined"
          style={uiStyles.input}
          disabled={submitting || resending}
          right={<TextInput.Icon icon={showPasswordConfirm ? 'eye-off' : 'eye'} onPress={() => setShowPasswordConfirm((visible) => !visible)} accessibilityLabel={showPasswordConfirm ? '비밀번호 확인 숨기기' : '비밀번호 확인 표시'} />}
          onSubmitEditing={() => void submit()}
        />
        <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
        <HelperText type="info" visible={Boolean(resendMessage)}>{resendMessage ?? ' '}</HelperText>
        <Button mode="contained" onPress={() => void submit()} loading={submitting} disabled={submitting || resending} contentStyle={uiStyles.primaryButton}>비밀번호 변경</Button>
        <Button mode="outlined" onPress={() => void resend()} loading={resending} disabled={submitting || resending || !email}>인증번호 다시 받기</Button>
        <Button mode="text" onPress={editEmail} disabled={submitting || resending}>이메일 다시 입력</Button>
      </Card.Content></Card>
    </Screen>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  container: { paddingVertical: spacing.xxxl },
  noticeCard: { backgroundColor: colors.blue100, borderRadius: radius.lg },
  noticeContent: { gap: spacing.sm },
  noticeText: { color: colors.navy900, lineHeight: 21 },
  emailText: { color: colors.blue700 },
  card: { borderRadius: radius.lg },
  form: { gap: spacing.md, paddingVertical: spacing.sm },
});

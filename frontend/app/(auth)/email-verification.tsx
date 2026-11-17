import { authApi } from '@/src/api/auth';
import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Button, Card, HelperText, Icon, Text, TextInput } from 'react-native-paper';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const RESEND_SECONDS = 60;
const DELIVERY_NOTICE = '입력한 이메일로 인증번호를 발송했습니다.\n메일이 도착하지 않으면 스팸함을 확인해 주세요.';

function requestErrorMessage(cause: unknown): string {
  if (!(cause instanceof ApiError)) return '인증번호 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status === 0) return '네트워크 연결을 확인한 후 다시 시도해 주세요.';
  if (cause.status === 422) return '올바른 이메일 형식인지 확인해 주세요.';
  if (cause.status === 429) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status >= 500) return '서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  return '인증번호 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
}

function confirmErrorMessage(cause: unknown): string {
  if (!(cause instanceof ApiError)) return '이메일 인증을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status === 0) return '네트워크 연결을 확인한 후 다시 시도해 주세요.';
  if (cause.status === 400) return '인증번호가 올바르지 않거나 만료되었습니다.';
  if (cause.status === 422) return '이메일과 인증번호를 다시 확인해 주세요.';
  if (cause.status === 429) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status >= 500) return '서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  return '이메일 인증을 처리하지 못했습니다. 입력값을 확인해 주세요.';
}

export default function EmailVerificationScreen() {
  const router = useRouter();
  const { resetSession } = useAuth();
  const params = useLocalSearchParams<{ email?: string; autoRequest?: string }>();
  const email = typeof params.email === 'string' ? params.email.trim() : '';
  const autoRequest = params.autoRequest === '1';
  const [code, setCode] = useState('');
  const [notice, setNotice] = useState<string>();
  const [error, setError] = useState<string>();
  const [requesting, setRequesting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState(0);
  const [completed, setCompleted] = useState(false);
  const requestRef = useRef(false);
  const confirmRef = useRef(false);
  const autoRequestedRef = useRef(false);

  const goToLogin = useCallback(() => {
    router.dismissTo({ pathname: '/login', params: completed ? { emailVerified: 'success', verifiedEmail: email } : {} });
  }, [completed, email, router]);

  const requestCode = useCallback(async () => {
    if (requestRef.current || confirmRef.current || secondsRemaining > 0) return;
    if (!email || !EMAIL_PATTERN.test(email)) {
      setError('올바른 이메일 주소가 필요합니다. 로그인 또는 회원가입 화면에서 이메일을 다시 확인해 주세요.');
      return;
    }

    requestRef.current = true;
    setRequesting(true);
    setError(undefined);
    try {
      await authApi.requestEmailVerification({ email });
      setCode('');
      setNotice(DELIVERY_NOTICE);
      setSecondsRemaining(RESEND_SECONDS);
    } catch (cause) {
      setError(requestErrorMessage(cause));
    } finally {
      requestRef.current = false;
      setRequesting(false);
    }
  }, [email, secondsRemaining]);

  useEffect(() => {
    if (!autoRequest || autoRequestedRef.current) return;
    autoRequestedRef.current = true;
    void requestCode();
  }, [autoRequest, requestCode]);

  useEffect(() => {
    if (secondsRemaining <= 0) return;
    const timeout = setTimeout(() => setSecondsRemaining((current) => Math.max(0, current - 1)), 1000);
    return () => clearTimeout(timeout);
  }, [secondsRemaining]);

  const confirm = async () => {
    if (confirmRef.current || requestRef.current) return;
    if (!email || !EMAIL_PATTERN.test(email)) {
      setError('올바른 이메일 주소가 필요합니다.');
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

    confirmRef.current = true;
    setConfirming(true);
    setError(undefined);
    try {
      const response = await authApi.confirmEmailVerification({ email, code });
      if (!response.verified) {
        setError('이메일 인증을 완료하지 못했습니다. 다시 시도해 주세요.');
        return;
      }
      setCode('');
      setNotice(undefined);
      await resetSession();
      setCompleted(true);
    } catch (cause) {
      setError(confirmErrorMessage(cause));
    } finally {
      confirmRef.current = false;
      setConfirming(false);
    }
  };

  if (completed) {
    return <Screen scroll contentStyle={styles.completedContainer}>
      <Card mode="outlined" style={[uiStyles.card, styles.completedCard]}><Card.Content style={styles.completedContent}>
        <Icon source="check-circle" size={56} color={colors.success} />
        <Text variant="headlineSmall" style={styles.completedTitle}>이메일 인증이 완료되었습니다.</Text>
        <Text variant="bodyLarge" style={styles.completedText}>회원가입이 완료되었습니다.{"\n"}새 계정으로 로그인해 주세요.</Text>
        <Button mode="contained" onPress={goToLogin} contentStyle={uiStyles.primaryButton}>로그인으로 이동</Button>
      </Card.Content></Card>
    </Screen>;
  }

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.container}>
      <PageHeader title="이메일 인증" subtitle="회원가입을 완료하려면 이메일 인증이 필요합니다." onBack={goToLogin} />
      <Card mode="contained" style={styles.emailCard}><Card.Content style={styles.emailContent}>
        <Text variant="labelMedium" style={styles.emailLabel}>인증할 이메일</Text>
        <Text variant="titleMedium" style={styles.emailText} selectable>{email || '이메일 정보가 없습니다.'}</Text>
      </Card.Content></Card>
      {notice && <Card mode="contained" style={styles.noticeCard}><Card.Content><Text variant="bodyMedium" style={styles.noticeText}>{notice}</Text></Card.Content></Card>}
      <Card mode="outlined" style={[uiStyles.card, styles.formCard]}><Card.Content style={styles.form}>
        <TextInput
          label="6자리 인증번호"
          value={code}
          onChangeText={(value) => { setCode(value.replace(/\D/g, '').slice(0, 6)); setError(undefined); }}
          keyboardType="number-pad"
          maxLength={6}
          mode="outlined"
          style={uiStyles.input}
          disabled={requesting || confirming}
          onSubmitEditing={() => void confirm()}
        />
        <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
        <Button mode="contained" onPress={() => void confirm()} loading={confirming} disabled={requesting || confirming || !email} contentStyle={uiStyles.primaryButton}>인증번호 확인</Button>
        <Button
          mode="outlined"
          icon="email-send-outline"
          onPress={() => void requestCode()}
          loading={requesting}
          disabled={requesting || confirming || secondsRemaining > 0 || !email}
        >
          {secondsRemaining > 0 ? `${secondsRemaining}초 후 재전송` : notice ? '인증번호 재전송' : '인증번호 받기'}
        </Button>
        <Button mode="text" onPress={goToLogin} disabled={requesting || confirming}>로그인으로 돌아가기</Button>
      </Card.Content></Card>
    </Screen>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  container: { paddingVertical: spacing.xxxl },
  emailCard: { backgroundColor: colors.navy900, borderRadius: radius.lg },
  emailContent: { gap: spacing.xs },
  emailLabel: { color: colors.blue100 },
  emailText: { color: '#FFFFFF', fontWeight: '700' },
  noticeCard: { backgroundColor: colors.blue100, borderRadius: radius.lg },
  noticeText: { color: colors.navy900, lineHeight: 21 },
  formCard: { borderRadius: radius.lg },
  form: { gap: spacing.md, paddingVertical: spacing.sm },
  completedContainer: { justifyContent: 'center', paddingVertical: spacing.xxxl },
  completedCard: { borderRadius: radius.lg },
  completedContent: { alignItems: 'center', gap: spacing.lg, paddingVertical: spacing.xxl },
  completedTitle: { color: colors.navy900, fontWeight: '800', textAlign: 'center' },
  completedText: { color: colors.textMuted, textAlign: 'center', lineHeight: 25 },
});

import { authApi } from '@/src/api/auth';
import { ApiError } from '@/src/api/client';
import { PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { radius, spacing } from '@/src/constants/theme';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Button, Card, HelperText, TextInput } from 'react-native-paper';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function requestErrorMessage(cause: unknown): string {
  if (!(cause instanceof ApiError)) return '인증번호 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status === 0) return '네트워크 연결을 확인한 후 다시 시도해 주세요.';
  if (cause.status === 422) return '올바른 이메일 형식으로 입력해 주세요.';
  if (cause.status === 429) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
  if (cause.status >= 500) return '서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  return '인증번호 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
}

export default function PasswordResetRequestScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ email?: string }>();
  const [email, setEmail] = useState(typeof params.email === 'string' ? params.email : '');
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);

  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/login');
  };

  const submit = async () => {
    if (submittingRef.current) return;
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setError('이메일을 입력해 주세요.');
      return;
    }
    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setError('올바른 이메일 형식으로 입력해 주세요.');
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError(undefined);
    try {
      await authApi.requestPasswordReset({ email: normalizedEmail });
      router.push({ pathname: '/password-reset/confirm', params: { email: normalizedEmail } });
    } catch (cause) {
      setError(requestErrorMessage(cause));
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.container}>
      <PageHeader title="비밀번호 재설정" subtitle="가입할 때 사용한 이메일을 입력해 주세요." onBack={goBack} />
      <Card mode="outlined" style={[uiStyles.card, styles.card]}><Card.Content style={styles.form}>
        <TextInput
          label="이메일"
          value={email}
          onChangeText={(value) => { setEmail(value); setError(undefined); }}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          mode="outlined"
          style={uiStyles.input}
          error={Boolean(error)}
          onSubmitEditing={() => void submit()}
        />
        <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
        <Button mode="contained" onPress={() => void submit()} loading={submitting} disabled={submitting} contentStyle={uiStyles.primaryButton}>인증번호 받기</Button>
        <Button mode="text" onPress={goBack} disabled={submitting}>로그인으로 돌아가기</Button>
      </Card.Content></Card>
    </Screen>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  container: { justifyContent: 'center', paddingVertical: spacing.xxxl },
  card: { borderRadius: radius.lg },
  form: { gap: spacing.md, paddingVertical: spacing.sm },
});

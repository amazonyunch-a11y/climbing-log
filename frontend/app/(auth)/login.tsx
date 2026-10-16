import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import { Button, Card, HelperText, Icon, Text, TextInput } from 'react-native-paper';
import { Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';

export default function LoginScreen() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!email.trim() || !password) {
      setError('이메일과 비밀번호를 입력해 주세요.');
      return;
    }
    setSubmitting(true);
    setError(undefined);
    try {
      await login({ email: email.trim(), password });
      router.replace('/(app)/(tabs)');
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '로그인에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.container}>
      <View style={styles.brand}><View style={styles.logo}><Icon source="terrain" size={34} color="#FFFFFF" /></View><Text variant="headlineLarge" style={styles.title}>Climbing Log</Text><Text variant="bodyLarge" style={styles.subtitle}>오늘의 움직임을 차분히 기록하세요.</Text></View>
      <Card mode="outlined" style={[uiStyles.card, styles.card]}><Card.Content style={styles.form}>
        <Text variant="titleLarge" style={styles.formTitle}>로그인</Text>
        <TextInput label="이메일" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email" keyboardType="email-address" mode="outlined" style={uiStyles.input} />
        <TextInput label="비밀번호" value={password} onChangeText={setPassword} secureTextEntry autoComplete="password" mode="outlined" style={uiStyles.input} onSubmitEditing={submit} />
        <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
        <Button mode="contained" onPress={submit} loading={submitting} disabled={submitting} contentStyle={uiStyles.primaryButton}>로그인</Button>
        <Link href="/signup" asChild><Button mode="text" disabled={submitting}>처음이신가요? 계정 만들기</Button></Link>
      </Card.Content></Card>
    </Screen>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  container: { justifyContent: 'center', paddingVertical: spacing.xxxl },
  brand: { alignItems: 'center', gap: spacing.sm },
  logo: { width: 64, height: 64, borderRadius: radius.lg, backgroundColor: colors.navy900, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.sm },
  title: { color: colors.navy950, fontWeight: '800', letterSpacing: -0.7 },
  subtitle: { color: colors.textMuted, textAlign: 'center' },
  card: { borderRadius: radius.lg },
  form: { gap: spacing.md, paddingVertical: spacing.sm },
  formTitle: { color: colors.navy900, fontWeight: '700', marginBottom: spacing.xs },
});

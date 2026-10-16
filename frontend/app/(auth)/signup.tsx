import { ApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Button, Card, HelperText, Text, TextInput } from 'react-native-paper';
import { Screen, PageHeader, uiStyles } from '@/src/components/ui';
import { radius, spacing } from '@/src/constants/theme';

export default function SignupScreen() {
  const { signup } = useAuth();
  const router = useRouter();
  const [nickname, setNickname] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!nickname.trim() || !email.trim() || !password) {
      setError('닉네임, 이메일, 비밀번호를 모두 입력해 주세요.');
      return;
    }
    setSubmitting(true);
    setError(undefined);
    try {
      await signup({ nickname: nickname.trim(), email: email.trim(), password });
      router.replace('/login');
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '회원가입에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.container}>
      <PageHeader title="계정 만들기" subtitle="기록을 안전하게 보관할 계정을 만들어 주세요." onBack={() => router.back()} />
      <Card mode="outlined" style={[uiStyles.card, styles.card]}><Card.Content style={styles.form}>
        <TextInput label="닉네임" value={nickname} onChangeText={setNickname} autoComplete="name" mode="outlined" style={uiStyles.input} />
        <TextInput label="이메일" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email" keyboardType="email-address" mode="outlined" style={uiStyles.input} />
        <TextInput label="비밀번호" value={password} onChangeText={setPassword} secureTextEntry autoComplete="new-password" mode="outlined" style={uiStyles.input} onSubmitEditing={submit} />
        <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
        <Button mode="contained" onPress={submit} loading={submitting} disabled={submitting} contentStyle={uiStyles.primaryButton}>회원가입</Button>
        <Button mode="text" onPress={() => router.back()} disabled={submitting}>이미 계정이 있어요</Button>
      </Card.Content></Card>
    </Screen>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({ root: { flex: 1 }, container: { justifyContent: 'center', paddingVertical: spacing.xxxl }, card: { borderRadius: radius.lg }, form: { gap: spacing.md, paddingVertical: spacing.sm } });

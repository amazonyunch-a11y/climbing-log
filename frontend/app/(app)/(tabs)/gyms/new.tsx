import { gymsApi } from '@/src/api/gyms';
import { ApiError } from '@/src/api/client';
import { GymForm } from '@/src/components/GymForm';
import { PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { spacing } from '@/src/constants/theme';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Card } from 'react-native-paper';

export default function NewGymScreen() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  const createGym = async (values: { name: string; location: string }) => {
    setIsSubmitting(true);
    setError(undefined);
    try {
      const gym = await gymsApi.create(values);
      router.replace({ pathname: '/gyms/[gymId]', params: { gymId: String(gym.id) } });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '암장을 등록하지 못했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}><Screen scroll><PageHeader title="암장 등록" subtitle="세션 기록에 사용할 암장 정보를 입력하세요." onBack={() => router.back()} /><Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.form}><GymForm submitLabel="등록하기" isSubmitting={isSubmitting} error={error} enablePlacePicker onSubmit={createGym} /></Card.Content></Card></Screen></KeyboardAvoidingView>;
}

const styles = StyleSheet.create({ root: { flex: 1 }, form: { gap: spacing.md } });

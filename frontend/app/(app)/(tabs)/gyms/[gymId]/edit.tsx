import { gymsApi } from '@/src/api/gyms';
import { ApiError } from '@/src/api/client';
import { GymForm } from '@/src/components/GymForm';
import { ErrorState, LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { spacing } from '@/src/constants/theme';
import type { Gym } from '@/src/types/gym';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Card } from 'react-native-paper';

export default function EditGymScreen() {
  const router = useRouter();
  const { gymId } = useLocalSearchParams<{ gymId: string }>();
  const id = Number(gymId);
  const [gym, setGym] = useState<Gym>();
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  const goBack = () => router.canGoBack() ? router.back() : router.replace('/gyms');

  useEffect(() => {
    async function loadGym() {
      if (!Number.isInteger(id)) { setError('잘못된 암장 ID입니다.'); setIsLoading(false); return; }
      try { setGym(await gymsApi.get(id)); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '암장 정보를 불러오지 못했습니다.'); } finally { setIsLoading(false); }
    }
    void loadGym();
  }, [id]);

  const updateGym = async (values: { name: string; location: string }) => {
    setIsSubmitting(true);
    setError(undefined);
    try { await gymsApi.update(id, values); router.replace({ pathname: '/gyms/[gymId]', params: { gymId: String(id) } }); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '암장을 수정하지 못했습니다.'); } finally { setIsSubmitting(false); }
  };

  if (isLoading) return <Screen><PageHeader title="암장 수정" onBack={goBack} /><LoadingState label="암장 정보를 불러오는 중입니다." /></Screen>;
  if (!gym) return <Screen><PageHeader title="암장 수정" onBack={goBack} /><ErrorState message={error ?? '암장 정보를 찾을 수 없습니다.'} /></Screen>;

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}><Screen scroll><PageHeader title="암장 수정" subtitle="암장 이름과 위치를 변경할 수 있어요." onBack={goBack} /><Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.form}><GymForm initialName={gym.name} initialLocation={gym.location} submitLabel="수정 저장" isSubmitting={isSubmitting} error={error} onSubmit={updateGym} /></Card.Content></Card></Screen></KeyboardAvoidingView>;
}

const styles = StyleSheet.create({ root: { flex: 1 }, form: { gap: spacing.md } });

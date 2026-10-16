import { gymsApi } from '@/src/api/gyms';
import { ApiError } from '@/src/api/client';
import { ConfirmDialog, ErrorState, LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { Gym } from '@/src/types/gym';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Icon, Snackbar, Text } from 'react-native-paper';

export default function GymDetailScreen() {
  const router = useRouter();
  const { gymId } = useLocalSearchParams<{ gymId: string }>();
  const id = Number(gymId);
  const [gym, setGym] = useState<Gym>();
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteDialogVisible, setDeleteDialogVisible] = useState(false);
  const [error, setError] = useState<string>();

  const goBackToGyms = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }
    router.replace('/gyms');
  };

  const loadGym = useCallback(async () => {
    if (!Number.isInteger(id)) { setError('잘못된 암장 ID입니다.'); setIsLoading(false); return; }
    setIsLoading(true);
    setError(undefined);
    try { setGym(await gymsApi.get(id)); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '암장 정보를 불러오지 못했습니다.'); } finally { setIsLoading(false); }
  }, [id]);

  useFocusEffect(useCallback(() => { void loadGym(); }, [loadGym]));

  const confirmDelete = async () => {
    setIsDeleting(true);
    setError(undefined);
    try { await gymsApi.remove(id); setDeleteDialogVisible(false); router.replace('/(app)/(tabs)/gyms'); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '암장을 삭제하지 못했습니다.'); } finally { setIsDeleting(false); }
  };

  if (isLoading) return <Screen><PageHeader title="암장 상세" onBack={goBackToGyms} /><LoadingState label="암장 정보를 불러오는 중입니다." /></Screen>;
  if (!gym) return <Screen><PageHeader title="암장 상세" onBack={goBackToGyms} /><ErrorState message={error ?? '암장 정보를 찾을 수 없습니다.'} onRetry={() => void loadGym()} /></Screen>;

  return <Screen>
    <PageHeader title="암장 상세" onBack={goBackToGyms} />
    <Card mode="outlined" style={[uiStyles.card, styles.heroCard]}><Card.Content style={styles.cardContent}><View style={styles.gymIcon}><Icon source="map-marker" size={34} color={colors.blue600} /></View><Text variant="headlineSmall" style={styles.gymName}>{gym.name}</Text><Text variant="bodyLarge" style={styles.location}>{gym.location}</Text></Card.Content></Card>
    <View style={styles.actions}><Button mode="contained" icon="pencil-outline" onPress={() => router.push({ pathname: '/gyms/[gymId]/edit', params: { gymId: String(gym.id) } })} contentStyle={uiStyles.primaryButton}>수정</Button><Button mode="outlined" icon="delete-outline" textColor={colors.error} style={uiStyles.destructiveButton} onPress={() => setDeleteDialogVisible(true)} disabled={isDeleting} contentStyle={uiStyles.primaryButton}>삭제</Button></View>
    <ConfirmDialog visible={deleteDialogVisible} title="암장 삭제" message="이 암장을 삭제할까요? 연결된 기록이 있다면 삭제가 제한될 수 있습니다." busy={isDeleting} onCancel={() => setDeleteDialogVisible(false)} onConfirm={() => void confirmDelete()} />
    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)}>{error}</Snackbar>
  </Screen>;
}

const styles = StyleSheet.create({ heroCard: { borderRadius: radius.lg }, cardContent: { alignItems: 'center', gap: spacing.md, paddingVertical: spacing.xl }, gymIcon: { width: 64, height: 64, borderRadius: radius.lg, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' }, gymName: { color: colors.navy900, fontWeight: '800', textAlign: 'center' }, location: { color: colors.textMuted, textAlign: 'center', lineHeight: 24 }, actions: { gap: spacing.md } });

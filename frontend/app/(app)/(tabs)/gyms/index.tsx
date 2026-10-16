import { gymsApi } from '@/src/api/gyms';
import { ApiError } from '@/src/api/client';
import { EmptyState, LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { colors, radius, spacing } from '@/src/constants/theme';
import type { Gym } from '@/src/types/gym';
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, StyleSheet, View } from 'react-native';
import { Button, Card, Icon, Snackbar, Text } from 'react-native-paper';

export default function GymsScreen() {
  const router = useRouter();
  const [gyms, setGyms] = useState<Gym[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>();

  const loadGyms = useCallback(async () => {
    setIsLoading(true);
    setError(undefined);
    try {
      setGyms(await gymsApi.list());
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '암장 목록을 불러오지 못했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void loadGyms(); }, [loadGyms]));

  if (isLoading) return <Screen><PageHeader title="암장" subtitle="내가 등록한 클라이밍 공간" /><LoadingState label="암장 목록을 불러오는 중입니다." /></Screen>;

  return <Screen>
    <PageHeader title="암장" subtitle="내가 등록한 클라이밍 공간" action={<Button mode="contained" icon="plus" compact onPress={() => router.push('/gyms/new')}>등록</Button>} />
    {gyms.length === 0 ? <EmptyState title="등록된 암장이 없어요" description="자주 가는 암장을 등록하고 세션 기록에 활용하세요." icon="map-marker-plus-outline" action={<Button mode="contained-tonal" onPress={() => router.push('/gyms/new')}>암장 등록</Button>} /> :
      <FlatList data={gyms} keyExtractor={(gym) => String(gym.id)} contentContainerStyle={styles.list} showsVerticalScrollIndicator={false} renderItem={({ item }) =>
        <Card mode="outlined" style={uiStyles.card} onPress={() => router.push({ pathname: '/gyms/[gymId]', params: { gymId: String(item.id) } })}><Card.Content style={styles.gymCard}><View style={styles.gymIcon}><Icon source="map-marker-outline" size={24} color={colors.blue600} /></View><View style={styles.gymText}><Text variant="titleMedium" style={styles.gymName} numberOfLines={2}>{item.name}</Text><Text variant="bodyMedium" style={uiStyles.muted} numberOfLines={3}>{item.location}</Text></View><Icon source="chevron-right" size={22} color={colors.textMuted} /></Card.Content></Card>
      } />}
    <Snackbar visible={Boolean(error)} onDismiss={() => setError(undefined)} action={{ label: '다시 시도', onPress: () => void loadGyms() }}>{error}</Snackbar>
  </Screen>;
}

const styles = StyleSheet.create({
  list: { gap: spacing.md, paddingBottom: spacing.xxxl },
  gymCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md }, gymIcon: { width: 46, height: 46, borderRadius: radius.md, backgroundColor: colors.sky100, alignItems: 'center', justifyContent: 'center' }, gymText: { flex: 1, gap: spacing.xs }, gymName: { color: colors.navy900, fontWeight: '700' },
});

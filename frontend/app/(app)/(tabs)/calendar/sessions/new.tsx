import { gymsApi } from '@/src/api/gyms';
import { ApiError } from '@/src/api/client';
import { sessionsApi } from '@/src/api/sessions';
import { SessionTimePicker } from '@/src/components/SessionTimePicker';
import { EmptyState, LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { spacing } from '@/src/constants/theme';
import type { Gym } from '@/src/types/gym';
import { combineKstDateAndTime, formatKstDate, parseKstInputToApi } from '@/src/utils/date';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Button, Card, HelperText, Menu, Text, TextInput } from 'react-native-paper';

export default function NewSessionScreen() {
  const router = useRouter();
  const { date } = useLocalSearchParams<{ date?: string }>();
  const sessionDate = date ?? formatKstDate(new Date());
  const [gyms, setGyms] = useState<Gym[]>([]);
  const [gymId, setGymId] = useState<number>();
  const [menuVisible, setMenuVisible] = useState(false);
  const [startedTime, setStartedTime] = useState('18:00');
  const [endedTime, setEndedTime] = useState<string>();
  const [notes, setNotes] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => { void (async () => {
    try { setGyms(await gymsApi.list()); } catch (cause) { setError(cause instanceof ApiError ? cause.message : '암장 목록을 불러오지 못했습니다.'); } finally { setIsLoading(false); }
  })(); }, []);

  const createSession = async () => {
    if (!gymId || !startedTime) { setError('암장과 운동 시작 시간을 입력해 주세요.'); return; }
    if (endedTime && endedTime <= startedTime) { setError('종료 시간은 시작 시간보다 늦어야 합니다.'); return; }
    let startedAtApi: string;
    let endedAtApi: string | null;
    try {
      startedAtApi = parseKstInputToApi(combineKstDateAndTime(sessionDate, startedTime));
      endedAtApi = endedTime ? parseKstInputToApi(combineKstDateAndTime(sessionDate, endedTime)) : null;
    } catch (cause) { setError(cause instanceof Error ? cause.message : '시간 형식이 올바르지 않습니다.'); return; }
    setIsSubmitting(true); setError(undefined);
    try {
      await sessionsApi.create({ gym_id: gymId, session_date: sessionDate, started_at: startedAtApi, ended_at: endedAtApi, total_attempts: 0, total_sends: 0, notes: notes.trim() || null });
      router.back();
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : '세션을 만들지 못했습니다.'); } finally { setIsSubmitting(false); }
  };

  if (isLoading) return <Screen><PageHeader title="세션 추가" onBack={() => router.back()} /><LoadingState label="암장 목록을 불러오는 중입니다." /></Screen>;
  if (gyms.length === 0) return <Screen><PageHeader title="세션 추가" onBack={() => router.back()} /><EmptyState title="등록된 암장이 없어요" description="세션을 만들려면 먼저 암장을 등록해 주세요." icon="map-marker-plus-outline" action={<Button mode="contained" onPress={() => router.push('/gyms')}>암장 등록하기</Button>} /></Screen>;

  const selectedGym = gyms.find((gym) => gym.id === gymId);
  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}><Screen scroll>
    <PageHeader title="세션 추가" subtitle={`${sessionDate} 운동 기록`} onBack={() => router.back()} />
    <Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.form}>
      <Text variant="labelLarge">암장</Text><Menu visible={menuVisible} onDismiss={() => setMenuVisible(false)} anchor={<Button mode="outlined" icon="map-marker-outline" contentStyle={styles.selectContent} onPress={() => setMenuVisible(true)}>{selectedGym?.name ?? '암장을 선택하세요'}</Button>}>{gyms.map((gym) => <Menu.Item key={gym.id} title={`${gym.name} · ${gym.location}`} onPress={() => { setGymId(gym.id); setMenuVisible(false); }} />)}</Menu>
      <SessionTimePicker label="시작 시간" sessionDate={sessionDate} value={startedTime} onChange={(time) => setStartedTime(time ?? '')} />
      <SessionTimePicker label="종료 시간 (선택)" sessionDate={sessionDate} value={endedTime} emptyLabel="종료 시간 없음 (진행 중)" clearable onChange={setEndedTime} />
      <TextInput label="메모 (선택)" value={notes} onChangeText={setNotes} mode="outlined" multiline numberOfLines={3} style={uiStyles.input} />
      <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
    </Card.Content></Card>
    <Button mode="contained" onPress={createSession} loading={isSubmitting} disabled={isSubmitting} contentStyle={uiStyles.primaryButton}>세션 저장</Button>
  </Screen></KeyboardAvoidingView>;
}

const styles = StyleSheet.create({ root: { flex: 1 }, form: { gap: spacing.md }, selectContent: { minHeight: 48, justifyContent: 'flex-start' } });

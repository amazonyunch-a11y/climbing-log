import { gymsApi } from '@/src/api/gyms';
import { ApiError } from '@/src/api/client';
import { sessionsApi } from '@/src/api/sessions';
import { SessionTimePicker } from '@/src/components/SessionTimePicker';
import { ErrorState, LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { spacing } from '@/src/constants/theme';
import type { Gym } from '@/src/types/gym';
import type { Session } from '@/src/types/session';
import { combineKstDateAndTime, formatKstDateTimeInput, parseKstInputToApi } from '@/src/utils/date';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { Button, Card, HelperText, Menu, Text, TextInput } from 'react-native-paper';

export default function EditSessionScreen() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const id = Number(sessionId);
  const [session, setSession] = useState<Session>();
  const [gyms, setGyms] = useState<Gym[]>([]);
  const [gymId, setGymId] = useState<number>();
  const [sessionDate, setSessionDate] = useState('');
  const [startedTime, setStartedTime] = useState('');
  const [endedTime, setEndedTime] = useState<string>();
  const [notes, setNotes] = useState('');
  const [menuVisible, setMenuVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  const goBack = () => router.canGoBack() ? router.back() : router.replace('/calendar');

  useEffect(() => { void (async () => {
    if (!Number.isInteger(id)) { setError('잘못된 세션 ID입니다.'); setIsLoading(false); return; }
    try {
      const [loadedSession, loadedGyms] = await Promise.all([sessionsApi.get(id), gymsApi.list()]);
      setSession(loadedSession); setGyms(loadedGyms); setGymId(loadedSession.gym_id); setSessionDate(loadedSession.session_date); setStartedTime(formatKstDateTimeInput(loadedSession.started_at).slice(11)); setEndedTime(loadedSession.ended_at ? formatKstDateTimeInput(loadedSession.ended_at).slice(11) : undefined); setNotes(loadedSession.notes ?? '');
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : '세션 정보를 불러오지 못했습니다.'); } finally { setIsLoading(false); }
  })(); }, [id]);

  const save = async () => {
    if (!gymId || !/^\d{4}-\d{2}-\d{2}$/.test(sessionDate) || !startedTime) { setError('암장과 운동 시작 시간을 입력해 주세요.'); return; }
    if (endedTime && endedTime <= startedTime) { setError('종료 시간은 시작 시간보다 늦어야 합니다.'); return; }
    let startedAtApi: string;
    let endedAtApi: string | null;
    try {
      startedAtApi = parseKstInputToApi(combineKstDateAndTime(sessionDate, startedTime));
      endedAtApi = endedTime ? parseKstInputToApi(combineKstDateAndTime(sessionDate, endedTime)) : null;
    } catch (cause) { setError(cause instanceof Error ? cause.message : '시간 형식이 올바르지 않습니다.'); return; }
    setIsSubmitting(true); setError(undefined);
    try {
      await sessionsApi.update(id, { gym_id: gymId, session_date: sessionDate, started_at: startedAtApi, ended_at: endedAtApi, notes: notes.trim() || null });
      router.replace({ pathname: '/calendar/sessions/[sessionId]', params: { sessionId: String(id) } });
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : '세션을 수정하지 못했습니다.'); } finally { setIsSubmitting(false); }
  };

  if (isLoading) return <Screen><PageHeader title="세션 수정" onBack={goBack} /><LoadingState label="세션 정보를 불러오는 중입니다." /></Screen>;
  if (!session) return <Screen><PageHeader title="세션 수정" onBack={goBack} /><ErrorState message={error ?? '세션을 찾을 수 없습니다.'} /></Screen>;
  const selectedGym = gyms.find((gym) => gym.id === gymId);
  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}><Screen scroll>
    <PageHeader title="세션 수정" subtitle={`${sessionDate} 운동 기록`} onBack={goBack} />
    <Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.form}>
      <Text variant="labelLarge">암장</Text><Menu visible={menuVisible} onDismiss={() => setMenuVisible(false)} anchor={<Button mode="outlined" icon="map-marker-outline" contentStyle={styles.selectContent} onPress={() => setMenuVisible(true)}>{selectedGym?.name ?? '암장을 선택하세요'}</Button>}>{gyms.map((gym) => <Menu.Item key={gym.id} title={`${gym.name} · ${gym.location}`} onPress={() => { setGymId(gym.id); setMenuVisible(false); }} />)}</Menu>
      <SessionTimePicker label="시작 시간" sessionDate={sessionDate} value={startedTime} onChange={(time) => setStartedTime(time ?? '')} />
      <SessionTimePicker label="종료 시간 (선택)" sessionDate={sessionDate} value={endedTime} emptyLabel="종료 시간 없음 (진행 중)" clearable onChange={setEndedTime} />
      <TextInput label="메모 (선택)" value={notes} onChangeText={setNotes} mode="outlined" multiline numberOfLines={3} style={uiStyles.input} />
      <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
    </Card.Content></Card>
    <Button mode="contained" onPress={save} loading={isSubmitting} disabled={isSubmitting} contentStyle={uiStyles.primaryButton}>수정 저장</Button><Button mode="text" onPress={goBack} disabled={isSubmitting}>취소</Button>
  </Screen></KeyboardAvoidingView>;
}

const styles = StyleSheet.create({ root: { flex: 1 }, form: { gap: spacing.md }, selectContent: { minHeight: 48, justifyContent: 'flex-start' } });

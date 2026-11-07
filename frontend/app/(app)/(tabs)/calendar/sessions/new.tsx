import { ApiError } from '@/src/api/client';
import { gymsApi } from '@/src/api/gyms';
import { sessionsApi } from '@/src/api/sessions';
import { stopwatchApi } from '@/src/api/stopwatch';
import { SessionTimePicker } from '@/src/components/SessionTimePicker';
import { StopwatchPendingNotice } from '@/src/components/StopwatchPendingNotice';
import { EmptyState, ErrorState, LoadingState, PageHeader, Screen, uiStyles } from '@/src/components/ui';
import { spacing } from '@/src/constants/theme';
import type { Gym } from '@/src/types/gym';
import type { SessionCreateResponse } from '@/src/types/session';
import type { Stopwatch } from '@/src/types/stopwatch';
import {
  combineKstDateAndTime,
  formatKstDate,
  formatKstTime,
  parseKstInputToApi,
} from '@/src/utils/date';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Button, Card, HelperText, Menu, Text, TextInput } from 'react-native-paper';

export default function NewSessionScreen() {
  const router = useRouter();
  const { date } = useLocalSearchParams<{ date?: string }>();
  const sessionDate = date ?? formatKstDate(new Date());
  const [gyms, setGyms] = useState<Gym[]>([]);
  const [gymId, setGymId] = useState<number>();
  const [menuVisible, setMenuVisible] = useState(false);
  const [startedTime, setStartedTime] = useState('18:00');
  const [endedTime, setEndedTime] = useState<string>();
  const [startedTimeEdited, setStartedTimeEdited] = useState(false);
  const [endedTimeEdited, setEndedTimeEdited] = useState(false);
  const [notes, setNotes] = useState('');
  const [pendingStopwatches, setPendingStopwatches] = useState<Stopwatch[]>([]);
  const [selectedStopwatchId, setSelectedStopwatchIdState] = useState<number | null>(null);
  const [autoSelected, setAutoSelected] = useState(false);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState<string>();
  const [pendingReloadVersion, setPendingReloadVersion] = useState(0);
  const [createdSession, setCreatedSession] = useState<SessionCreateResponse>();
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  const pendingRequestId = useRef(0);
  const selectedStopwatchIdRef = useRef<number | null>(null);
  const autoSelectionAllowedRef = useRef(true);

  const setSelectedStopwatchId = useCallback((value: number | null) => {
    selectedStopwatchIdRef.current = value;
    setSelectedStopwatchIdState(value);
  }, []);

  const applyStopwatch = useCallback((stopwatch: Stopwatch, automatic: boolean) => {
    setSelectedStopwatchId(stopwatch.id);
    setStartedTime(formatKstTime(stopwatch.startedAt));
    setEndedTime(stopwatch.endedAt ? formatKstTime(stopwatch.endedAt) : undefined);
    setStartedTimeEdited(false);
    setEndedTimeEdited(false);
    setAutoSelected(automatic);
    if (!automatic) autoSelectionAllowedRef.current = false;
  }, [setSelectedStopwatchId]);

  useEffect(() => {
    void (async () => {
      try {
        setGyms(await gymsApi.list());
      } catch (cause) {
        setError(cause instanceof ApiError ? cause.message : '암장 목록을 불러오지 못했습니다.');
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    pendingRequestId.current += 1;
    autoSelectionAllowedRef.current = true;
    setPendingStopwatches([]);
    setSelectedStopwatchId(null);
    setAutoSelected(false);
    setStartedTime('18:00');
    setEndedTime(undefined);
    setStartedTimeEdited(false);
    setEndedTimeEdited(false);
    setPendingError(undefined);
  }, [sessionDate, setSelectedStopwatchId]);

  useEffect(() => {
    const requestId = ++pendingRequestId.current;
    let disposed = false;
    setPendingLoading(true);
    setPendingError(undefined);

    void (async () => {
      try {
        const response = await stopwatchApi.getPending(sessionDate);
        if (disposed || requestId !== pendingRequestId.current) return;

        const sameDateStopwatches = response.filter(
          (stopwatch) => formatKstDate(stopwatch.startedAt) === sessionDate,
        );
        setPendingStopwatches(sameDateStopwatches);

        const currentSelection = selectedStopwatchIdRef.current;
        const currentSelectionStillExists = currentSelection != null
          && sameDateStopwatches.some((stopwatch) => stopwatch.id === currentSelection);
        if (currentSelection != null && !currentSelectionStillExists) {
          setSelectedStopwatchId(null);
          setAutoSelected(false);
          autoSelectionAllowedRef.current = false;
        }
        if (
          selectedStopwatchIdRef.current == null
          && sameDateStopwatches.length === 1
          && autoSelectionAllowedRef.current
        ) {
          applyStopwatch(sameDateStopwatches[0], true);
        }
      } catch {
        if (disposed || requestId !== pendingRequestId.current) return;
        setPendingError('저장된 운동 시간을 불러오지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.');
      } finally {
        if (!disposed && requestId === pendingRequestId.current) setPendingLoading(false);
      }
    })();

    return () => { disposed = true; };
  }, [applyStopwatch, pendingReloadVersion, sessionDate, setSelectedStopwatchId]);

  const selectStopwatch = (stopwatch: Stopwatch) => {
    applyStopwatch(stopwatch, false);
    setError(undefined);
  };

  const clearStopwatchSelection = () => {
    setSelectedStopwatchId(null);
    setAutoSelected(false);
    setStartedTimeEdited(true);
    setEndedTimeEdited(true);
    autoSelectionAllowedRef.current = false;
  };

  const changeStartedTime = (value?: string) => {
    setStartedTime(value ?? '');
    setStartedTimeEdited(true);
    setAutoSelected(false);
    autoSelectionAllowedRef.current = false;
  };

  const changeEndedTime = (value?: string) => {
    setEndedTime(value);
    setEndedTimeEdited(true);
    setAutoSelected(false);
    autoSelectionAllowedRef.current = false;
  };

  const createSession = async () => {
    if (!gymId || !startedTime) {
      setError('암장과 운동 시작 시간을 입력해 주세요.');
      return;
    }

    const selectedStopwatch = pendingStopwatches.find(
      (stopwatch) => stopwatch.id === selectedStopwatchId,
    );
    let startedAtApi: string;
    let endedAtApi: string | null;
    try {
      startedAtApi = selectedStopwatch && !startedTimeEdited
        ? selectedStopwatch.startedAt
        : parseKstInputToApi(combineKstDateAndTime(sessionDate, startedTime));
      endedAtApi = selectedStopwatch && !endedTimeEdited
        ? selectedStopwatch.endedAt
        : endedTime
          ? parseKstInputToApi(combineKstDateAndTime(sessionDate, endedTime))
          : null;
      if (endedAtApi && new Date(endedAtApi).getTime() <= new Date(startedAtApi).getTime()) {
        setError('종료 시간은 시작 시간보다 늦어야 합니다.');
        return;
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '시간 형식이 올바르지 않습니다.');
      return;
    }

    setIsSubmitting(true);
    setError(undefined);
    try {
      setCreatedSession(await sessionsApi.create({
        gym_id: gymId,
        session_date: sessionDate,
        started_at: startedAtApi,
        ended_at: endedAtApi,
        total_attempts: 0,
        total_sends: 0,
        notes: notes.trim() || null,
        stopwatch_id: selectedStopwatch?.id ?? null,
      }));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : '세션을 만들지 못했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <Screen><PageHeader title="세션 추가" onBack={() => router.back()} /><LoadingState label="암장 목록을 불러오는 중입니다." /></Screen>;
  if (gyms.length === 0) return <Screen><PageHeader title="세션 추가" onBack={() => router.back()} /><EmptyState title="등록된 암장이 없어요" description="세션을 만들려면 먼저 암장을 등록해 주세요." icon="map-marker-plus-outline" action={<Button mode="contained" onPress={() => router.push('/gyms')}>암장 등록하기</Button>} /></Screen>;

  if (createdSession) {
    const linkedStopwatch = createdSession.stopwatch_id != null;
    const usesStopwatchTimes = createdSession.duration_source === 'stopwatch';
    return <Screen>
      <PageHeader title="세션 저장 완료" onBack={() => router.replace({ pathname: '/calendar', params: { date: sessionDate } })} />
      <Card mode="outlined" style={uiStyles.card}>
        <Card.Content style={styles.form}>
          <Text variant="titleLarge">
            {usesStopwatchTimes
              ? '저장된 운동 시간이 세션에 연결되었습니다.'
              : linkedStopwatch
                ? '저장된 운동 기록을 연결하고 수정한 시간으로 저장했습니다.'
                : '세션이 저장되었습니다.'}
          </Text>
          <Text variant="bodyMedium">
            {usesStopwatchTimes
              ? '운동 시간과 시작·종료 시간이 선택한 Stopwatch 기록을 기준으로 반영되었습니다.'
              : linkedStopwatch
                ? 'Stopwatch 연결은 유지되며 직접 수정한 시작·종료 시간을 사용합니다.'
                : '직접 입력한 운동 시간이 저장되었습니다.'}
          </Text>
          <Button mode="contained" onPress={() => router.replace({ pathname: '/calendar/sessions/[sessionId]', params: { sessionId: String(createdSession.id) } })}>세션 상세보기</Button>
          <Button mode="outlined" onPress={() => router.replace({ pathname: '/calendar', params: { date: sessionDate } })}>캘린더로 돌아가기</Button>
        </Card.Content>
      </Card>
    </Screen>;
  }

  const selectedGym = gyms.find((gym) => gym.id === gymId);
  const selectedStopwatch = pendingStopwatches.find(
    (stopwatch) => stopwatch.id === selectedStopwatchId,
  );
  const hasEditedSelectedTime = selectedStopwatch != null
    && (startedTimeEdited || endedTimeEdited);

  return <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <Screen scroll contentStyle={styles.screenContent}>
      <PageHeader title="세션 추가" subtitle={`${sessionDate} 운동 기록`} onBack={() => router.back()} />
      {pendingLoading && pendingStopwatches.length === 0 && <Card mode="outlined" style={uiStyles.card}><Card.Content style={styles.pendingLoading}><ActivityIndicator /><Text variant="bodyMedium" style={uiStyles.muted}>저장된 운동 시간을 확인하는 중입니다.</Text></Card.Content></Card>}
      {pendingStopwatches.length > 0 && <StopwatchPendingNotice
        stopwatches={pendingStopwatches}
        selectedStopwatchId={selectedStopwatchId}
        onSelect={selectStopwatch}
        onClearSelection={clearStopwatchSelection}
        autoSelected={autoSelected}
      />}
      {pendingError && <ErrorState message={pendingError} onRetry={() => setPendingReloadVersion((value) => value + 1)} />}
      <Card mode="outlined" style={uiStyles.card}>
        <Card.Content style={styles.form}>
          <Text variant="labelLarge">암장</Text>
          <Menu
            visible={menuVisible}
            onDismiss={() => setMenuVisible(false)}
            anchor={<Button mode="outlined" icon="map-marker-outline" contentStyle={styles.selectContent} onPress={() => setMenuVisible(true)}>{selectedGym?.name ?? '암장을 선택하세요'}</Button>}
          >
            {gyms.map((gym) => <Menu.Item key={gym.id} title={`${gym.name} · ${gym.location}`} onPress={() => { setGymId(gym.id); setMenuVisible(false); }} />)}
          </Menu>
          <SessionTimePicker label="시작 시간" sessionDate={sessionDate} value={startedTime} onChange={changeStartedTime} />
          <SessionTimePicker label="종료 시간 (선택)" sessionDate={sessionDate} value={endedTime} emptyLabel="종료 시간 없음 (진행 중)" clearable onChange={changeEndedTime} />
          {selectedStopwatch && <View style={styles.timeSourceNotice}>
            <Text variant="bodySmall" style={uiStyles.muted}>
              {hasEditedSelectedTime
                ? '선택한 운동 기록은 연결하되, 사용자가 수정한 시작·종료 시간을 우선합니다.'
                : '선택한 운동 기록의 시작·종료 시간이 자동으로 반영되었습니다.'}
            </Text>
          </View>}
          <TextInput label="메모 (선택)" value={notes} onChangeText={setNotes} mode="outlined" multiline numberOfLines={3} style={uiStyles.input} />
          <HelperText type="error" visible={Boolean(error)}>{error ?? ' '}</HelperText>
        </Card.Content>
      </Card>
      <Button mode="contained" onPress={createSession} loading={isSubmitting} disabled={isSubmitting} contentStyle={uiStyles.primaryButton}>세션 저장</Button>
    </Screen>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  screenContent: { paddingBottom: spacing.xxxl * 3 },
  form: { gap: spacing.md },
  selectContent: { minHeight: 48, justifyContent: 'flex-start' },
  pendingLoading: { minHeight: 88, alignItems: 'center', justifyContent: 'center', gap: spacing.sm },
  timeSourceNotice: { paddingHorizontal: spacing.sm },
});

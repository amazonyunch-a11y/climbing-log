import { PlaceholderScreen } from '@/src/components/PlaceholderScreen';
import { useLocalSearchParams } from 'expo-router';

export default function DateSessionsScreen() {
  const { date } = useLocalSearchParams<{ date: string }>();
  return <PlaceholderScreen title={`${date} 세션`} description="이 날짜의 세션 목록과 새 운동 기록 버튼이 여기에 추가됩니다." />;
}

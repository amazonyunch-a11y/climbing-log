import { AuthProvider, useAuth } from '@/src/auth/AuthProvider';
import { theme } from '@/src/constants/theme';
import { Redirect, Stack, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, Provider as PaperProvider, Surface } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

function AuthGate() {
  const { user, isLoading } = useAuth();
  const segments = useSegments();
  const inAuthGroup = segments[0] === '(auth)';

  if (isLoading) {
    return <Surface style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}><ActivityIndicator size="large" /></Surface>;
  }

  if (!user && !inAuthGroup) return <Redirect href="/login" />;
  if (user && (inAuthGroup || !segments[0])) return <Redirect href="/(app)/(tabs)" />;

  return <Stack screenOptions={{ headerShown: false }} />;
}

export default function RootLayout() {
  return <SafeAreaProvider><PaperProvider theme={theme}><StatusBar style="dark" /><AuthProvider><AuthGate /></AuthProvider></PaperProvider></SafeAreaProvider>;
}

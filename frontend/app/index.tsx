import { Redirect } from 'expo-router';

// AuthGate normally intercepts this route. This fallback prevents a blank root screen.
export default function Index() {
  return <Redirect href="/login" />;
}

import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '@/src/constants/theme';
import { Tabs } from 'expo-router';

export default function TabsLayout() {
  return <Tabs screenOptions={{
    headerShown: false,
    tabBarActiveTintColor: colors.blue600,
    tabBarInactiveTintColor: colors.textMuted,
    tabBarStyle: { height: 66, paddingTop: 7, paddingBottom: 8, backgroundColor: colors.surface, borderTopColor: colors.border },
    tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
  }}>
    <Tabs.Screen name="index" options={{ title: '홈', tabBarIcon: ({ color, size, focused }) => <MaterialCommunityIcons name={focused ? 'home' : 'home-outline'} color={color} size={size} /> }} />
    <Tabs.Screen name="calendar" options={{ title: '캘린더', tabBarIcon: ({ color, size, focused }) => <MaterialCommunityIcons name={focused ? 'calendar-month' : 'calendar-month-outline'} color={color} size={size} /> }} />
    <Tabs.Screen name="gyms" options={{ title: '암장', tabBarIcon: ({ color, size, focused }) => <MaterialCommunityIcons name={focused ? 'map-marker' : 'map-marker-outline'} color={color} size={size} /> }} />
    <Tabs.Screen name="statistics" options={{ title: '통계', tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="chart-bar" color={color} size={size} /> }} />
    <Tabs.Screen name="profile" options={{ title: '프로필', tabBarIcon: ({ color, size, focused }) => <MaterialCommunityIcons name={focused ? 'account' : 'account-outline'} color={color} size={size} /> }} />
  </Tabs>;
}

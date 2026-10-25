import { Stack, router } from 'expo-router';
import { View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SessionProvider, useSession } from '../session';
import { IconButton, Loading } from '../ui';
import { useTheme } from '../theme';
import { AttendanceToast, useAttendanceAlerts } from '../notifications';

function Navigation() {
  const { ready, username, api } = useSession();
  const { colors: c, isDark } = useTheme();
  const alerts = useAttendanceAlerts(username ? api : null, 'notifications/');
  if (!ready) return <View style={{ flex: 1, justifyContent: 'center', padding: 24, backgroundColor: c.background }}><Loading /></View>;
  return <><StatusBar style={isDark ? 'light' : 'dark'} /><Stack screenOptions={{ headerTintColor: c.ink, headerStyle: { backgroundColor: c.background }, headerShadowVisible: false, headerTitleStyle: { fontWeight: '600' }, contentStyle: { backgroundColor: c.background } }}>
    <Stack.Protected guard={!username}><Stack.Screen name="login" options={{ title: 'PL admin', headerRight: () => <IconButton icon="settings-outline" label="Settings" onPress={() => router.push('/settings')} /> }} /><Stack.Screen name="settings" options={{ title: 'Settings' }} /></Stack.Protected>
    <Stack.Protected guard={!!username}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="employee/[id]" options={{ title: 'Employee attendance' }} />
      <Stack.Screen name="employee/create" options={{ title: 'Add employee' }} />
      <Stack.Screen name="activity" options={{ title: 'Attendance activity' }} />
    </Stack.Protected>

  </Stack><AttendanceToast text={alerts.text} onDismiss={alerts.dismiss} /></>;
}
export default function Layout() { return <SessionProvider><Navigation /></SessionProvider>; }

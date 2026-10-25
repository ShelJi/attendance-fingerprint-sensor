import { Tabs, router } from 'expo-router';
import { Icon, IconButton, type IconName } from '../../ui';
import { useTheme } from '../../theme';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useWindowDimensions } from 'react-native';
export default function Layout() {
  const { colors: c } = useTheme();
  const insets = useSafeAreaInsets();
  const { fontScale } = useWindowDimensions();
  const tabs: [string, string, IconName, IconName][] = [['index', 'Overview', 'grid-outline', 'grid'], ['employees', 'People', 'people-outline', 'people'], ['device', 'Device', 'finger-print-outline', 'finger-print'], ['calendar', 'Calendar', 'calendar-outline', 'calendar'], ['reports', 'Reports', 'stats-chart-outline', 'stats-chart']];
  return <Tabs screenOptions={{ tabBarActiveTintColor: c.primary, tabBarInactiveTintColor: c.muted, headerTintColor: c.ink, headerStyle: { backgroundColor: c.background }, headerTitleStyle: { fontWeight: '600' }, headerShadowVisible: false, sceneStyle: { backgroundColor: c.background }, tabBarLabelStyle: { fontSize: 12, lineHeight: 20, fontWeight: '600' }, tabBarItemStyle: { minHeight: 64 }, tabBarHideOnKeyboard: true, tabBarStyle: { height: Math.max(80, 60 + 20 * fontScale) + insets.bottom, paddingTop: 4, paddingBottom: Math.max(insets.bottom, 4), backgroundColor: c.surface, borderTopColor: c.line } }}>
    {tabs.map(([name, title, icon, activeIcon]) => <Tabs.Screen key={name} name={name} options={{ title, headerRight: () => <IconButton icon="notifications-outline" label="All attendance notifications" onPress={() => router.push('/activity')} />, tabBarIcon: ({ color, focused }) => <Icon name={focused ? activeIcon : icon} color={color} size={24} /> }} />)}
  </Tabs>;
}

import { Tabs, router } from 'expo-router';
import { Icon, IconButton, Row, type IconName } from '../../ui';
import { typography, sizing, tabBarHeight } from '../../design';
import { useTheme } from '../../theme';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text, useWindowDimensions } from 'react-native';
export default function Layout() {
  const { colors: c } = useTheme();
  const insets = useSafeAreaInsets();
  const { fontScale } = useWindowDimensions();
  const tabs: [string, string, IconName, IconName][] = [['index', 'Overview', 'grid-outline', 'grid'], ['employees', 'People', 'people-outline', 'people'], ['device', 'Device', 'finger-print-outline', 'finger-print'], ['calendar', 'Calendar', 'calendar-outline', 'calendar'], ['reports', 'Reports', 'stats-chart-outline', 'stats-chart']];
  return <Tabs screenOptions={{ tabBarActiveTintColor: c.primary, tabBarInactiveTintColor: c.muted, headerTintColor: c.ink, headerStyle: { backgroundColor: c.background }, headerTitleStyle: typography.label, headerShadowVisible: false, sceneStyle: { backgroundColor: c.background }, tabBarLabelStyle: { ...typography.caption, fontWeight: '600' }, tabBarItemStyle: { minHeight: sizing.touch }, tabBarHideOnKeyboard: true, tabBarStyle: { height: 'auto', minHeight: tabBarHeight(fontScale) + insets.bottom, paddingTop: 4, paddingBottom: Math.max(insets.bottom, 4), backgroundColor: c.surface, borderTopColor: c.line } }}>
    {tabs.map(([name, title, icon, activeIcon]) => <Tabs.Screen key={name} name={name} options={{ title, tabBarLabel: ({ color }) => <Text style={{ ...typography.caption, fontWeight: '600', color, textAlign: 'center', alignSelf: 'stretch', flexShrink: 0 }}>{title}</Text>, headerRight: () => <Row><IconButton icon="notifications-outline" label="All attendance notifications" onPress={() => router.push('/activity')} /><IconButton icon="settings-outline" label="Settings" onPress={() => router.push('/settings')} /></Row>, tabBarIcon: ({ color, focused }) => <Icon name={focused ? activeIcon : icon} color={color} size={sizing.icon} /> }} />)}
  </Tabs>;
}

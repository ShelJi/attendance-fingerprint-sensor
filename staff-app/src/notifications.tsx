import { useEffect, useState } from 'react';
import { AppState, Platform } from 'react-native';
import Constants from 'expo-constants';
import { isRunningInExpoGo } from 'expo';
import { Api } from './api';

// Expo Go cannot load the push module included in our native app builds.
const Notifications: typeof import('expo-notifications') | null =
  // eslint-disable-next-line @typescript-eslint/no-require-imports -- Static imports run before the Expo Go guard.
  Platform.OS !== 'web' && !isRunningInExpoGo() ? require('expo-notifications') : null;

Notifications?.setNotificationHandler({
  handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }),
});

async function registerDevice(api: Api, stopped = () => false) {
  if (!Notifications) throw new Error('Use the installed app.');
  if (Platform.OS === 'android') await Notifications.setNotificationChannelAsync('attendance', {
    name: 'Attendance', importance: Notifications.AndroidImportance.HIGH, sound: 'default',
  });
  let permission = await Notifications.getPermissionsAsync();
  if (!permission.granted && permission.canAskAgain) permission = await Notifications.requestPermissionsAsync();
  if (!permission.granted) throw new Error('Notifications disabled.');
  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  if (!projectId) throw new Error('Notifications unavailable.');
  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  if (!stopped()) await api.post('notifications/device/', { token });
  return token;
}

export async function testNotification(api: Api, onSent: () => void = () => {}) {
  const token = await registerDevice(api);
  const notifications = Notifications!;
  const testId = Date.now().toString(36) + Math.random().toString(36).slice(2);
  let timer: ReturnType<typeof setTimeout> | undefined;
  let confirm!: (received: boolean) => void;
  const received = new Promise<boolean>(resolve => { confirm = resolve; });
  const listener = notifications.addNotificationReceivedListener(notification => {
    if (notification.request.content.data?.test_id === testId) confirm(true);
  });
  try {
    const result = await api.post<{ sent: boolean }>('notifications/test/', { token, test_id: testId });
    if (!result.sent) throw new Error('Not sent.');
    onSent();
    timer = setTimeout(() => confirm(false), 15000);
    return (await received) ? 'Received.' : 'Sent.';
  } finally {
    listener.remove();
    if (timer) clearTimeout(timer);
  }
}

export function useAttendanceAlerts(api: Api | null) {
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!api || !Notifications) return;
    const notifications = Notifications;
    let stopped = false;
    let registering = false;
    async function register() {
      if (registering || stopped) return;
      registering = true;
      try {
        await registerDevice(api!, () => stopped);
        if (!stopped) setError('');
      } catch (e) {
        if (!stopped) setError((e as Error).message === 'Notifications disabled.' ? 'Notifications disabled.' : 'Notifications unavailable.');
      } finally { registering = false; }
    }
    void register();
    const state = AppState.addEventListener('change', value => { if (value === 'active') void register(); });
    const tokens = notifications.addPushTokenListener(() => { void register(); });
    return () => { stopped = true; state.remove(); tokens.remove(); };
  }, [api, attempt]);
  return { error, retry: () => setAttempt(value => value + 1) };
}

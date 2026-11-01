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
        if (Platform.OS === 'android') await notifications.setNotificationChannelAsync('attendance', {
          name: 'Attendance', importance: notifications.AndroidImportance.HIGH, sound: 'default',
        });
        let permission = await notifications.getPermissionsAsync();
        if (!permission.granted && permission.canAskAgain) permission = await notifications.requestPermissionsAsync();
        if (!permission.granted) throw new Error('Allow notifications in your phone settings to receive attendance alerts.');
        const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
        if (!projectId) throw new Error('Push notifications need an EAS project ID in this app build.');
        const token = (await notifications.getExpoPushTokenAsync({ projectId })).data;
        if (stopped) return;
        await api!.post('notifications/device/', { token });
        if (!stopped) setError('');
      } catch (e) {
        if (!stopped) setError(`Notifications unavailable: ${(e as Error).message}`);
      } finally { registering = false; }
    }
    void register();
    const state = AppState.addEventListener('change', value => { if (value === 'active') void register(); });
    const tokens = notifications.addPushTokenListener(() => { void register(); });
    return () => { stopped = true; state.remove(); tokens.remove(); };
  }, [api, attempt]);
  return { error, retry: () => setAttempt(value => value + 1) };
}

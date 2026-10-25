import { Platform } from 'react-native';
import * as Location from 'expo-location';
import NetInfo from '@react-native-community/netinfo';

export type WorkMode = 'office' | 'outdoor';
export type Position = { latitude: number; longitude: number; accuracy: number; captured_at: string; mocked: boolean };

export async function captureVerification(mode: WorkMode) {
  if (Platform.OS === 'web') throw new Error('Use the Android or iOS app for location and Wi-Fi verification.');
  const permission = await Location.requestForegroundPermissionsAsync();
  if (!permission.granted) throw new Error('Precise location permission is required to record attendance. Enable it in your phone settings.');
  if (!await Location.hasServicesEnabledAsync()) throw new Error('Turn on your phone’s location services.');
  let timer: ReturnType<typeof setTimeout>;
  const point = await Promise.race([
    Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
    new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error('Location timed out. Move where GPS reception is better and try again.')), 30000); }),
  ]).finally(() => clearTimeout(timer));
  if (point.mocked) throw new Error('Simulated locations are not accepted. Turn off mock location and try again.');
  if (point.coords.accuracy == null || point.coords.accuracy <= 0 || point.coords.accuracy > 100) throw new Error('Location accuracy must be within 100 metres. Move where reception is better and try again.');
  const location: Position = { latitude: point.coords.latitude, longitude: point.coords.longitude, accuracy: point.coords.accuracy, captured_at: new Date(point.timestamp).toISOString(), mocked: false };
  if (mode === 'outdoor') return { location };
  NetInfo.configure({ shouldFetchWiFiSSID: Platform.OS === 'ios' });
  const network = await NetInfo.fetch('wifi');
  if (network.type !== 'wifi' || !network.isConnected || !network.details.ssid || !network.details.bssid) {
    throw new Error('Connect to your office Wi-Fi. The app needs permission to read its SSID/BSSID; iOS requires a signed build with Wi-Fi access enabled.');
  }
  return { location, wifi_ssid: network.details.ssid, wifi_bssid: network.details.bssid };
}

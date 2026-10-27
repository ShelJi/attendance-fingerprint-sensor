import { Platform } from 'react-native';
import * as Location from 'expo-location';
import NetInfo from '@react-native-community/netinfo';

export async function captureWifi() {
  if (Platform.OS === 'web') throw new Error('Browsers cannot read Wi-Fi names or BSSIDs. Use PL admin on an Android or iPhone connected to the Wi-Fi, or enter both fields manually.');
  if (!(await Location.requestForegroundPermissionsAsync()).granted) throw new Error('Allow precise location permission to read connected Wi-Fi, or enter the details manually.');
  if (!await Location.hasServicesEnabledAsync()) throw new Error('Enable location services to read connected Wi-Fi, or enter the details manually.');
  NetInfo.configure({ shouldFetchWiFiSSID: Platform.OS === 'ios' });
  const network = await NetInfo.fetch('wifi');
  if (network.type !== 'wifi' || !network.isConnected) throw new Error('Connect this phone to your office Wi-Fi or another phone’s hotspot first.');
  const ssid = network.details.ssid;
  const bssid = network.details.bssid?.toLowerCase();
  if (!ssid || ssid === '<unknown ssid>' || !bssid || !/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/.test(bssid) || ['02:00:00:00:00:00', '00:00:00:00:00:00'].includes(bssid)) {
    throw new Error('Wi-Fi details are unavailable. Allow precise location access; iPhone needs an app build with Wi-Fi access enabled. You can also enter both fields manually.');
  }
  return { wifi_ssid: ssid, wifi_bssid: bssid };
}

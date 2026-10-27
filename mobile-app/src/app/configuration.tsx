import { useCallback, useState } from 'react';
import { View } from 'react-native';
import * as Location from 'expo-location';
import { useSession } from '../session';
import { captureWifi } from '../wifi';
import { Badge, Body, Button, Card, Caption, Chip, ErrorText, Field, Loading, Screen, Section, useAction, useResource } from '../ui';

type Office = { id: number; name: string; is_active: boolean; wifi_ssid: string; wifi_bssid: string; latitude: number; longitude: number; radius_meters: number; max_accuracy_meters: number };
const empty = () => ({ name: '', is_active: true, wifi_ssid: '', wifi_bssid: '', latitude: '', longitude: '', radius_meters: '100', max_accuracy_meters: '50' });
const fields = [
  ['name', 'Office name'], ['wifi_ssid', 'Wi-Fi network name (SSID)'], ['wifi_bssid', 'Wi-Fi access-point BSSID'],
  ['latitude', 'Latitude'], ['longitude', 'Longitude'], ['radius_meters', 'Allowed radius (metres)'], ['max_accuracy_meters', 'Maximum GPS uncertainty (metres)'],
] as const;

export default function Configuration() {
  const { api } = useSession();
  const resource = useResource(useCallback(() => api!.get<{ offices: Office[] }>('configuration/offices/'), [api]));
  const [selected, setSelected] = useState<number | null>(null);
  const [draft, setDraft] = useState(empty);
  const [message, setMessage] = useState('');
  const action = useAction();
  function select(office?: Office) {
    setSelected(office?.id ?? null); setMessage('');
    setDraft(office ? { ...office, latitude: String(office.latitude), longitude: String(office.longitude), radius_meters: String(office.radius_meters), max_accuracy_meters: String(office.max_accuracy_meters) } : empty());
  }
  return <Screen><Section title="App configuration" detail="Set the office location and Wi-Fi used for staff attendance verification." />
    <ErrorText error={resource.error || action.error} />{resource.loading && <Loading />}
    <Card><Section title="Office configurations" detail="Select an office to update it, or add another office/access point." />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {resource.data?.offices.map(office => <Chip key={office.id} title={`${office.name}${office.is_active ? '' : ' (inactive)'}`} selected={selected === office.id} disabled={action.busy} onPress={() => select(office)} />)}
        <Chip title="Add office" selected={selected === null} disabled={action.busy} onPress={() => select()} />
      </View>
    </Card>
    <Card><Section title={selected ? 'Update office configuration' : 'Add office configuration'} />
      <Body>Stand at the office centre to capture GPS, or enter coordinates manually. Enter the router’s BSSID, not the phone’s MAC address. Wi-Fi passwords are not needed here.</Body>
      <Button title="Use current location" icon="locate-outline" variant="secondary" loading={action.busy} onPress={() => void action.run(async () => {
        setMessage('');
        if (!(await Location.requestForegroundPermissionsAsync()).granted) throw new Error('Allow location permission, or enter the office coordinates manually.');
        if (!await Location.hasServicesEnabledAsync()) throw new Error('Enable location services, or enter coordinates manually.');
        let timer: ReturnType<typeof setTimeout>;
        const point = await Promise.race([
          Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
          new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error('Location timed out. Try again or enter coordinates manually.')), 30000); }),
        ]).finally(() => clearTimeout(timer));
        if (point.mocked) throw new Error('Simulated locations cannot be used as the office location.');
        setDraft(value => ({ ...value, latitude: point.coords.latitude.toFixed(6), longitude: point.coords.longitude.toFixed(6) }));
        setMessage(`Location captured${point.coords.accuracy == null ? '' : ` (±${Math.round(point.coords.accuracy)} m)`}. Review it and save the configuration.`);
      })} />
      <Button title="Use connected Wi-Fi" icon="wifi-outline" variant="secondary" loading={action.busy} onPress={() => void action.run(async () => {
        setMessage('');
        const wifi = await captureWifi();
        setDraft(value => ({ ...value, ...wifi }));
        setMessage('Wi-Fi details captured. Review them and save the configuration.');
      })} />
      <Caption>Connect this phone to the office Wi-Fi or another phone’s hotspot before capturing. Browser users must enter Wi-Fi details manually.</Caption>
      {fields.map(([key, label]) => <Field key={key} label={label} value={draft[key]} editable={!action.busy} autoCorrect={false} placeholder={key === 'wifi_bssid' ? 'AA:BB:CC:DD:EE:FF' : undefined} keyboardType={['latitude', 'longitude', 'radius_meters', 'max_accuracy_meters'].includes(key) ? 'numbers-and-punctuation' : 'default'} onChangeText={value => { setMessage(''); setDraft(current => ({ ...current, [key]: value })); }} />)}
      <Chip title={draft.is_active ? 'Active · Accept office attendance' : 'Inactive · Office attendance disabled'} selected={draft.is_active} disabled={action.busy} onPress={() => { setMessage(''); setDraft(value => ({ ...value, is_active: !value.is_active })); }} />
      <Caption>Allowed radius: 10–1000 m. GPS uncertainty limit: 1–100 m. Changes apply to future office check-ins and check-outs.</Caption>
      <Button title="Save configuration" icon="save-outline" loading={action.busy} disabled={fields.some(([key]) => !draft[key].trim())} onPress={() => void action.run(async () => {
        setMessage('');
        const data = await api!.post<{ office: Office }>(`configuration/offices/${selected ? `${selected}/` : ''}`, {
          ...draft, latitude: Number(draft.latitude), longitude: Number(draft.longitude), radius_meters: Number(draft.radius_meters), max_accuracy_meters: Number(draft.max_accuracy_meters),
        });
        select(data.office); setMessage('Configuration saved. Staff attendance will use these settings on the next submission.');
        await resource.refresh();
      })} />
      {!!message && <Badge tone="teal">{message}</Badge>}
    </Card>
    <Button title="Refresh configurations" icon="refresh-outline" variant="ghost" disabled={resource.loading || action.busy} onPress={() => void resource.refresh()} />
  </Screen>;
}

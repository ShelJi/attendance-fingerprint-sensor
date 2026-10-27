import { useCallback, useEffect, useState } from 'react';
import { Alert, Platform, Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { useSession } from '../../session';
import { Command, Device } from '../../types';
import { Badge, Body, Button, Card, Caption, Chip, Column, ErrorText, Field, IconTile, Label, Loading, Row, Screen, Section, stamp, useAction, useResource } from '../../ui';
import { useTheme } from '../../theme';

const commands = ['LIST_IDS', 'ENROLL', 'ENROLL_AUTO', 'DELETE', 'REPLACE', 'VERIFY', 'SUMMARY', 'INFO'];
const labels: Record<string, string> = { LIST_IDS: 'Saved IDs', ENROLL: 'Enroll', ENROLL_AUTO: 'Auto enroll', DELETE: 'Delete', REPLACE: 'Replace', VERIFY: 'Verify', SUMMARY: 'Summary', INFO: 'Sensor info' };
const help: Record<string, string> = { LIST_IDS: 'List the fingerprints stored on your sensor.', ENROLL: 'Enroll a fingerprint at the ID you choose.', ENROLL_AUTO: 'Let the sensor choose an available fingerprint ID.', DELETE: 'Permanently remove a fingerprint from the sensor.', REPLACE: 'Replace the fingerprint assigned to an existing ID.', VERIFY: 'Ask someone at the sensor to verify their fingerprint.', SUMMARY: 'Get a summary of the sensor’s fingerprint database.', INFO: 'Check sensor information and capabilities.' };
export default function DeviceScreen() {
  const { colors: c } = useTheme();
  const { api } = useSession(); const [focused, setFocused] = useState(false);
  useFocusEffect(useCallback(() => { setFocused(true); return () => setFocused(false); }, []));
  const resource = useResource(useCallback(() => api!.get<{ device: Device | null }>('device/control/'), [api]));
  const [selected, setSelected] = useState('INFO'); const [finger, setFinger] = useState('');
  const [command, setCommand] = useState<Command>(); const [pollError, setPollError] = useState('');
  const action = useAction();
  const pending = command?.status === 'pending' || command?.status === 'running';
  const needsId = ['ENROLL', 'DELETE', 'REPLACE'].includes(selected);
  const commandId = command?.command_id;
  useEffect(() => {
    if (!pending || !commandId || !focused) return;
    let stopped = false; let timer: ReturnType<typeof setTimeout>;
    const deadline = Date.now() + 90000;
    async function poll() {
      try {
        const result = await api!.get<Command>(`device/control/result/?command_id=${commandId}`);
        if (stopped) return;
        setCommand({ ...result, command_id: commandId }); setPollError('');
        if (['pending', 'running'].includes(result.status)) {
          if (Date.now() < deadline) timer = setTimeout(poll, 2500);
          else setPollError('Still waiting for the sensor. Use Check result to try again.');
        }
      } catch (e) { if (!stopped) setPollError((e as Error).message); }
    }
    timer = setTimeout(poll, 1000);
    return () => { stopped = true; clearTimeout(timer); };
  }, [api, commandId, pending, focused]);
  function send() {
    void action.run(async () => {
      if (needsId && (!/^\d+$/.test(finger) || +finger < 1 || +finger > 127)) throw new Error('Fingerprint ID must be between 1 and 127.');
      setPollError('');
      setCommand(await api!.post<Command>('device/control/command/', { command: selected, ...(needsId ? { fingerprint_id: +finger } : {}) }));
    });
  }
  return <Screen><Section title="Connected to your workday" detail="Manage enrollment and keep your sensor in sync." /><ErrorText error={resource.error} />{resource.loading && <Loading />}
    <Card tone="teal"><Row><IconTile name="finger-print-outline" tone="teal" /><Column><Label>{resource.data?.device?.device_id || 'No device registered'}</Label><Caption>Attendance sensor</Caption></Column></Row><Badge tone={resource.data?.device?.is_online ? 'teal' : 'amber'}>{resource.data?.device?.is_online ? 'Online' : 'Offline'}</Badge><Body>Last seen {stamp(resource.data?.device?.last_seen || null)}</Body><Button title="Refresh status" icon="refresh-outline" variant="ghost" disabled={resource.loading} onPress={() => void resource.refresh()} /></Card>
    <Section title="What would you like to do?" /><Card><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{commands.map(name => <View key={name} style={{ flexGrow: 1, flexBasis: 128, minWidth: 0 }}><Chip title={labels[name]} selected={selected === name} onPress={() => setSelected(name)} disabled={action.busy || pending} tone={['DELETE', 'REPLACE'].includes(name) ? 'coral' : 'primary'} /></View>)}</View>
      <Body>{help[selected]}</Body>
      {needsId && <Field label="Fingerprint ID (1–127)" icon="finger-print-outline" placeholder="Enter sensor ID" value={finger} onChangeText={setFinger} keyboardType="number-pad" />}
      <Caption>Enrollment and verification require someone at the sensor.</Caption><ErrorText error={action.error} />
      <Button title={action.busy ? 'Sending…' : 'Send command'} icon="paper-plane-outline" loading={action.busy} disabled={pending || !resource.data?.device?.is_active} danger={selected === 'DELETE' || selected === 'REPLACE'} onPress={() => {
        if (['DELETE', 'REPLACE'].includes(selected)) {
          const message = `${selected} will change fingerprint ${finger} on the device.`;
          if (Platform.OS === 'web') { if (window.confirm(message)) send(); }
          else Alert.alert('Change sensor fingerprint?', message, [{ text: 'Cancel', style: 'cancel' }, { text: 'Continue', style: 'destructive', onPress: send }]);
        }
        else send();
      }} /></Card>
    {command && <Card><Row><IconTile name={pending ? 'hourglass-outline' : 'checkmark-circle-outline'} tone={command.status === 'failed' ? 'coral' : 'teal'} /><Column><Label>Command #{command.command_id}</Label><Caption>Sensor response</Caption></Column></Row><Badge tone={command.status === 'failed' ? 'coral' : pending ? 'amber' : 'teal'}>{command.status}</Badge><View style={{ borderRadius: 16, padding: 16, backgroundColor: c.soft }}><Text selectable style={{ color: c.ink, fontSize: 16, lineHeight: 24 }}>{JSON.stringify(command.result ?? command.message ?? 'Waiting for device…', null, 2)}</Text></View><ErrorText error={pollError} />
      <Button title="Check result" icon="refresh-outline" variant="secondary" disabled={action.busy} onPress={() => void action.run(async () => { const result = await api!.get<Command>(`device/control/result/?command_id=${command.command_id}`); setCommand({ ...result, command_id: command.command_id }); setPollError(''); })} />
      {pending && <Button title="Stop watching" icon="stop-circle-outline" variant="ghost" onPress={() => { setCommand(undefined); setPollError(''); }} />}
    </Card>}
  </Screen>;
}

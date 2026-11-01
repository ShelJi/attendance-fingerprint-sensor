import { useCallback, useState } from 'react';
import { router } from 'expo-router';
import { View } from 'react-native';
import { SessionCard } from '../../session-card';
import { useSession } from '../../session';
import { attendanceMessage, type Attendance } from '../../attendance';
import { captureVerification, type WorkMode } from '../../verification';
import { Body, Button, Card, Chip, ErrorText, Field, Hero, Loading, Row, Screen, Section, Stat, useAction, useResource } from '../../ui';

export default function Today() {
  const { api, username, signOut } = useSession();
  const resource = useResource(useCallback(() => api!.get<Attendance>('attendance/'), [api]));
  const action = useAction();
  const [mode, setMode] = useState<WorkMode>('office');
  const [place, setPlace] = useState('');
  const [description, setDescription] = useState('');
  const [status, setStatus] = useState('');
  const data = resource.data;
  const busy = action.busy || resource.loading;
  async function record() {
    if (!data) return;
    if (mode === 'outdoor' && (!place.trim() || !description.trim())) throw new Error('Enter place and work details.');
    if (mode === 'office' && !data.verification.office_configured) throw new Error('Office unavailable.');
    setStatus('Checking…');
    try {
      const proof = await captureVerification(mode);
      const result = await api!.post<Attendance>('attendance/', {
        action: data.checked_in ? 'logout' : 'login', mode, ...proof,
        ...(mode === 'outdoor' ? { place_name: place.trim(), work_description: description.trim() } : {}),
      });
      setStatus(attendanceMessage(result.action));
    } catch (error) { setStatus(''); throw error; }
    finally { await resource.refresh(); }
  }
  return <Screen>
    <Hero eyebrow="Your daily overview" title={`Hello, ${data?.employee.name || username}`} subtitle="Your attendance." icon="sunny-outline" />
    <ErrorText error={resource.error || action.error} />{resource.loading && <Loading />}
    {data && <>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}><Stat label="Today’s sessions" value={data.sessions.length} icon="calendar-outline" /><Stat label="Current status" value={data.checked_in ? 'Checked in' : 'Checked out'} icon="pulse-outline" tone="teal" /></View>
      <Card><Section title="Record your attendance" />
        <Row><Chip title="In office" selected={mode === 'office'} onPress={() => setMode('office')} /><Chip title="Outdoor" selected={mode === 'outdoor'} onPress={() => setMode('outdoor')} /></Row>
        {mode === 'office' ? <Body>{data.verification.office_configured ? 'Connect to the Wi-Fi.' : 'Office unavailable.'}</Body> : <>
          <Field label="Place name" value={place} onChangeText={setPlace} maxLength={200} editable={!busy} />
          <Field label="Today’s work description" value={description} onChangeText={setDescription} maxLength={4000} editable={!busy} multiline />
        </>}
        <Body>Location is shared with your admin.</Body>
        <Button title={data.checked_in ? 'Verify & check out' : 'Verify & check in'} icon="finger-print-outline" loading={action.busy} disabled={busy || (mode === 'office' && !data.verification.office_configured) || (mode === 'outdoor' && (!place.trim() || !description.trim()))} onPress={() => void action.run(record)} />
      </Card>
      <Section title="Today’s activity" />
      {!data.sessions.length && <Body>No attendance.</Body>}
      {data.sessions.map(item => <SessionCard key={item.id} session={item} />)}
    </>}
    {!!status && <Body>{status}</Body>}
    <Button title="My attendance activity" icon="notifications-outline" variant="secondary" onPress={() => router.push('/activity')} />
    <Button title="Refresh overview" icon="refresh-outline" variant="ghost" disabled={busy} onPress={() => void resource.refresh()} />
    <Button title="Sign out" icon="log-out-outline" variant="ghost" loading={action.busy} onPress={() => void action.run(signOut)} />
  </Screen>;
}

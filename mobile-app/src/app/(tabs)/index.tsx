import { useCallback } from 'react';
import { View } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../../session';
import { Dashboard } from '../../types';
import { Badge, Body, Button, Card, Column, ErrorText, Hero, IconTile, Label, Loading, Row, Screen, Section, Stat, stamp, useAction, useResource } from '../../ui';
export default function Overview() {
  const { api, username, signOut } = useSession();
  const resource = useResource(useCallback(() => api!.get<Dashboard>('dashboard/'), [api]));
  const action = useAction();
  const data = resource.data;
  return <Screen><Hero eyebrow="Your daily overview" title={`Hello, ${username}`} subtitle="A clear view of your people and their workday." icon="sunny-outline" />
    <ErrorText error={resource.error || action.error} />{resource.loading && <Loading />}
    {data && <><Section title="Today, at a glance" /><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 16 }}>
      <Stat label="Team members" value={data.total_employees} icon="people-outline" />
      <Stat label="Today’s sessions" value={data.today_sessions} icon="calendar-outline" tone="teal" />
      <Stat label="Active sessions" value={data.active_sessions} icon="pulse-outline" tone="coral" />
    </View><Section title="Your device" /><Card><Row><IconTile name="finger-print-outline" tone="teal" /><Column><Label>{data.device?.device_id || 'No device registered'}</Label><Body>Last seen {stamp(data.device?.last_seen || null)}</Body></Column></Row><Badge tone={data.device?.is_online ? 'teal' : 'amber'}>{data.device?.is_online ? 'Online · Ready for scans' : 'Offline · Awaiting connection'}</Badge><Button title="Open device controls" variant="secondary" icon="arrow-forward-outline" onPress={() => router.push('/device')} /></Card></>}
    <Section title="Keep the day moving" detail="The tools you use most, one tap away." /><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 16 }}><View style={{ flexGrow: 1, flexBasis: 160 }}><Button title="Your people" icon="people-outline" onPress={() => router.push('/employees')} /></View><View style={{ flexGrow: 1, flexBasis: 160 }}><Button title="View reports" icon="stats-chart-outline" variant="secondary" onPress={() => router.push('/reports')} /></View></View>
    <Button title="Refresh overview" variant="ghost" icon="refresh-outline" onPress={() => void resource.refresh()} disabled={resource.loading} />
    <Button title="Sign out" variant="ghost" icon="log-out-outline" onPress={() => void action.run(signOut)} loading={action.busy} />
  </Screen>;
}

import { useCallback, useState } from 'react';
import { Linking, View } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../session';
import { googleMapsUrl } from '../location';
import { monthRange } from '../dates';
import { query } from '../api';
import { Avatar, Badge, Body, Button, Card, Caption, Chip, Column, DateRange, EmptyState, ErrorText, IconButton, Label, Loading, Row, Screen, Section, stamp, useAction, useResource, validateRange } from '../ui';

type WorkMode = '' | 'office' | 'outdoor' | 'device';
type Record = {
  id: number; name: string; employee_id: number; employee_code: string; session_id: number;
  action: 'login' | 'logout'; mode: Exclude<WorkMode, ''>; occurred_at: string;
  verification: null | { office: string | null; latitude: number; longitude: number; accuracy_meters: number; captured_at: string; wifi_ssid: string; wifi_bssid: string; place_name: string; work_description: string };
};
type Activity = { records: Record[]; totals: { office: number; outdoor: number; device: number }; page: number; pages: number; count: number; has_next: boolean; has_previous: boolean };

export default function ActivityScreen() {
  const { api } = useSession();
  const [filter, setFilter] = useState(() => ({ ...monthRange(new Date()), mode: '' as WorkMode, page: 1 }));
  const [start, setStart] = useState(filter.start_date); const [end, setEnd] = useState(filter.end_date);
  const [showFilters, setShowFilters] = useState(false);
  const action = useAction();
  const resource = useResource(useCallback(() => api!.get<Activity>(`attendance/records/${query(filter)}`), [api, filter]));
  const data = resource.data;
  return <Screen><Section title="Every arrival. Every workday." detail="Office and outdoor attendance, with all check-in/out notifications and the verification details your team submitted." />
    <Card style={{ padding: 16 }}><Row><Column><Label>Showing attendance for</Label><Body>{filter.start_date || 'Month start'} — {filter.end_date || 'Month end'}</Body></Column><IconButton icon="options-outline" label={showFilters ? 'Hide date filters' : 'Change date range'} onPress={() => setShowFilters(!showFilters)} /></Row></Card>
    {showFilters && <DateRange start={start} end={end} onStart={setStart} onEnd={setEnd} disabled={resource.loading} onApply={() => void action.run(async () => { validateRange(start, end); setFilter({ ...filter, start_date: start, end_date: end, page: 1 }); setShowFilters(false); })} />}
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{([['', 'All'], ['office', 'Office'], ['outdoor', 'Outdoor'], ['device', 'Device / legacy']] as const).map(([mode, title]) => <Chip key={mode} title={title} selected={filter.mode === mode} onPress={() => setFilter({ ...filter, mode, page: 1 })} />)}</View>
    <ErrorText error={resource.error || action.error} />{resource.loading && <Loading />}
    {data && <><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}><Badge tone="teal">Office: {data.totals.office}</Badge><Badge tone="amber">Outdoor: {data.totals.outdoor}</Badge><Badge>Device / legacy: {data.totals.device}</Badge></View>
      {!data.records.length && <EmptyState icon="notifications-outline" title="No attendance in this view" message="Choose another workplace or date range to see more activity." />}
      {data.records.map(item => <Card key={item.id} tone={item.verification ? 'teal' : undefined}><Row><Avatar name={item.name} tone={item.mode === 'outdoor' ? 'amber' : 'teal'} /><Column><Label>{item.name}</Label><Caption>{item.employee_code} · Session #{item.session_id}</Caption></Column></Row>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}><Badge tone={item.action === 'login' ? 'teal' : 'primary'}>{item.action === 'login' ? 'Checked in' : 'Checked out'}</Badge><Badge tone={item.mode === 'outdoor' ? 'amber' : 'primary'}>{item.mode === 'device' ? 'Device / legacy' : item.mode === 'office' ? 'Office' : 'Outdoor'}</Badge></View><Body>{stamp(item.occurred_at)}</Body>
        {item.verification ? <>
          <Section title={item.verification.office || item.verification.place_name} />
          <Body>GPS · {item.verification.latitude.toFixed(6)}, {item.verification.longitude.toFixed(6)}{'\n'}Accuracy · ±{Math.round(item.verification.accuracy_meters)} m</Body><Caption>Captured {stamp(item.verification.captured_at)}</Caption>
          {item.mode === 'office' ? <Body>Wi-Fi · {item.verification.wifi_ssid}{'\n'}BSSID · {item.verification.wifi_bssid}</Body> : <><Label>Day’s work</Label><Body>{item.verification.work_description}</Body></>}
          <Button title={item.action === 'login' ? 'Check-in location' : 'Check-out location'} variant="secondary" icon="location-outline" onPress={() => void action.run(async () => { await Linking.openURL(googleMapsUrl(item.verification!.latitude, item.verification!.longitude)); })} />
        </> : <Body>Device or historical attendance. No mobile Wi-Fi/GPS evidence was recorded.</Body>}
        <Button title="Employee attendance" variant="ghost" icon="person-outline" onPress={() => router.push({ pathname: '/employee/[id]', params: { id: item.employee_id } })} />
      </Card>)}
      <Caption>Page {data.page} of {data.pages} · {data.count} events</Caption><Row><Column><Button title="Previous" variant="secondary" disabled={!data.has_previous} onPress={() => setFilter({ ...filter, page: data.page - 1 })} /></Column><Column><Button title="Next" variant="secondary" disabled={!data.has_next} onPress={() => setFilter({ ...filter, page: data.page + 1 })} /></Column></Row>
    </>}
    <Button title="Refresh activity" icon="refresh-outline" variant="ghost" disabled={resource.loading} onPress={() => void resource.refresh()} /><Caption>Attendance history is saved here. Phone notifications are delivered even when the app is closed. Refresh to load the latest records.</Caption>
  </Screen>;
}

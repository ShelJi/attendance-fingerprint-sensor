import { useCallback, useState } from 'react';
import { View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useSession } from '../../session';
import { query } from '../../api';
import { SessionCard } from '../../session-card';
import { Detail } from '../../types';
import { Avatar, Badge, Body, Button, Card, Caption, Column, DateRange, EmptyState, ErrorText, Label, Loading, Row, Screen, Section, Title, useAction, useResource, validateRange } from '../../ui';
export default function EmployeeDetail() {
  const { id } = useLocalSearchParams<{ id: string }>(); const { api } = useSession();
  const [start, setStart] = useState(''); const [end, setEnd] = useState('');
  const [filter, setFilter] = useState({ start_date: '', end_date: '', page: 1 });
  const action = useAction();
  const resource = useResource(useCallback(() => api!.get<Detail>(`employees/${id}/${query(filter)}`), [api, id, filter]));
  const data = resource.data;
  return <Screen>{data ? <Row><Avatar name={data.employee.name} /><Column><Section title={data.employee.name} /><Caption>{data.employee.employee_id} · Fingerprint {data.employee.fingerprint_id}</Caption></Column></Row> : <Section title="Employee attendance" />}
    <DateRange start={start} end={end} onStart={setStart} onEnd={setEnd} disabled={resource.loading} onApply={() => void action.run(async () => { validateRange(start, end); setFilter({ start_date: start, end_date: end, page: 1 }); })} />
    <ErrorText error={action.error || resource.error} />{resource.loading && <Loading />}
    {data && <><Card tone="primary"><Label>Total worked</Label><Title>{data.total_worked}</Title><Badge>{data.page_obj.count} sessions</Badge></Card><Section title="Session timeline" />
      {data.page_obj.results.map(row => <SessionCard key={row.id} session={row} showDuration />)}
      {!data.page_obj.count && <EmptyState icon="time-outline" title="No sessions in this range" message="Try a wider date range to see more attendance." />}
      <Body>Page {data.page_obj.page} of {data.page_obj.pages}</Body>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}><View style={{ flex: 1, minWidth: 120 }}><Button title="Previous" icon="chevron-back-outline" variant="secondary" disabled={!data.page_obj.has_previous} onPress={() => setFilter({ ...filter, page: data.page_obj.page - 1 })} /></View><View style={{ flex: 1, minWidth: 120 }}><Button title="Next" icon="chevron-forward-outline" variant="secondary" disabled={!data.page_obj.has_next} onPress={() => setFilter({ ...filter, page: data.page_obj.page + 1 })} /></View></View></>}
    <Button title="Refresh attendance" variant="ghost" icon="refresh-outline" disabled={resource.loading} onPress={() => void resource.refresh()} />
  </Screen>;
}

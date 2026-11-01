import { useCallback, useState } from 'react';
import { View } from 'react-native';
import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { query } from '../../api';
import { monthRange } from '../../dates';
import { useSession } from '../../session';
import { LoginSourceFilter, LoginSourceBadges, type LoginSource } from '../../login-source';
import { Report } from '../../types';
import { Avatar, Badge, Body, Button, Card, Caption, Column, DateRange, Divider, EmptyState, ErrorText, Hero, Label, Loading, Row, Screen, Section, stamp, useAction, useResource, validateRange } from '../../ui';
export default function Reports() {
  const { api } = useSession();
  const [filter, setFilter] = useState(() => ({ ...monthRange(new Date()), source: 'all' as LoginSource }));
  const [start, setStart] = useState(filter.start_date); const [end, setEnd] = useState(filter.end_date);
  const action = useAction();
  const resource = useResource(useCallback(() => api!.get<Report>(`report/${query(filter)}`), [api, filter]));
  const data = resource.data;
  return <Screen><Section title="The bigger picture" detail="Turn your team’s workdays into clear, shareable reports." />
    <LoginSourceFilter value={filter.source} disabled={resource.loading || action.busy} onChange={source => setFilter({ ...filter, source })} />
    <DateRange start={start} end={end} onStart={setStart} onEnd={setEnd} disabled={resource.loading || action.busy} onApply={() => void action.run(async () => { validateRange(start, end); setFilter({ ...filter, start_date: start, end_date: end }); })} />
    <ErrorText error={resource.error || action.error} />{resource.loading && <Loading />}
    {data && <><Hero eyebrow="Total time worked" title={data.grand_total} subtitle={`${data.start_date} to ${data.end_date}`} icon="stats-chart-outline"><Row><Badge>{data.total_records} daily records</Badge><Badge>{data.report_data.length} people</Badge></Row></Hero>
      <Button title={action.busy ? 'Preparing PDF…' : 'Share / save PDF'} icon="download-outline" loading={action.busy} onPress={() => void action.run(async () => {
        if (!await Sharing.isAvailableAsync()) throw new Error('File sharing is unavailable on this device.');
        const response = await api!.response(`report/pdf/${query({ start_date: data.start_date, end_date: data.end_date, source: filter.source })}`);
        if (!response.headers.get('content-type')?.includes('application/pdf')) throw new Error('The server did not return a PDF.');
        const file = new File(Paths.cache, `attendance-${Date.now()}.pdf`);
        try {
          await file.write(new Uint8Array(await response.arrayBuffer()));
          await Sharing.shareAsync(file.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: 'Attendance report' });
        } finally { if (file.exists) file.delete(); }
      })} />
      <Section title="Your team’s breakdown" />{data.report_data.length === 0 && <EmptyState icon="stats-chart-outline" title="No records in this range" message="Try another period to build your attendance report." />}
      {data.report_data.map(group => <Card key={group.employee.id}><Row><Avatar name={group.employee.name} /><Column><Label>{group.employee.name}</Label><Caption>{group.employee.employee_id}</Caption></Column></Row><Badge tone="teal">{group.employee_total} total worked</Badge>{group.records.map(row => <View key={row.date} style={{ gap: 12 }}><Divider /><Row><Column><Label>{row.date}</Label><Caption>{row.sessions} sessions</Caption></Column><Badge>{row.worked_hours}</Badge></Row><LoginSourceBadges {...row} /><Body>In · {stamp(row.login_at)}{'\n'}Out · {stamp(row.logout_at)}</Body></View>)}</Card>)}</>}
    <Button title="Refresh reports" variant="ghost" icon="refresh-outline" disabled={resource.loading} onPress={() => void resource.refresh()} />
  </Screen>;
}

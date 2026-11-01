import { useCallback, useState } from 'react';
import { Pressable, Text, View, useWindowDimensions } from 'react-native';
import { useSession } from '../../session';
import { Calendar, Day } from '../../types';
import { Avatar, Badge, Body, Button, Card, Caption, Column, EmptyState, ErrorText, Field, IconButton, Label, Loading, Row, Screen, Section, dateValid, hours, useAction, useResource } from '../../ui';
import { clockTime, dateKey, monthCells, shiftMonth } from '../../dates';
import { sizing, spacing, typography } from '../../design';
import { LoginSourceFilter, LoginSourceBadges, type LoginSource } from '../../login-source';
import { SessionCard } from '../../session-card';
import { useTheme } from '../../theme';
export default function CalendarScreen() {
  const { api } = useSession(); const today = new Date();
  const { colors: c } = useTheme(); const { width } = useWindowDimensions();
  const [source, setSource] = useState<LoginSource>('all');
  const [jump, setJump] = useState(false);
  const [year, setYear] = useState(String(today.getFullYear())); const [month, setMonth] = useState(String(today.getMonth() + 1));
  const [period, setPeriod] = useState({ year, month }); const [date, setDate] = useState(''); const [day, setDay] = useState<Day>();
  const action = useAction();
  const resource = useResource(useCallback(() => api!.get<Calendar>(`calendar/?year=${period.year}&month=${period.month}&source=${source}`), [api, period, source]));
  async function loadDay(value: string, selectedSource = source) {
    await action.run(async () => { if (!dateValid(value)) throw new Error('Invalid date.'); setDay(undefined); setDay(await api!.get<Day>(`calendar/day/?date=${value}&source=${selectedSource}`)); });
  }
  const busy = action.busy || resource.loading;
  const monthName = new Date(2000, +period.month - 1).toLocaleString(undefined, { month: 'long' });
  const records = new Map(resource.data?.calendar_days.map(item => [item.date, item]));
  const selectedRecord = records.get(date);
  function move(step: number) {
    const next = shiftMonth(+period.year, +period.month, step);
    const value = { year: String(next.year).padStart(4, '0'), month: String(next.month) };
    setYear(value.year); setMonth(value.month); setDay(undefined); setDate(''); setPeriod(value);
  }
  return <Screen><Section title="Every day tells a story" />
    <LoginSourceFilter value={source} disabled={busy} onChange={value => { setSource(value); setDay(undefined); if (dateValid(date)) void loadDay(date, value); }} />
    <Card style={{ marginHorizontal: width < 360 ? -spacing.sm : 0, padding: 0 }}>
      <View style={{ padding: 12, gap: 12 }}><Row><IconButton icon="chevron-back" label="Previous month" disabled={busy || (+period.year === 1 && +period.month === 1)} onPress={() => move(-1)} /><Column><Section title={monthName} /><Caption>{period.year}</Caption></Column><IconButton icon="chevron-forward" label="Next month" disabled={busy || (+period.year === 9998 && +period.month === 12)} onPress={() => move(1)} /></Row>
        <Row><Column><Badge tone="teal">{resource.data ? `${resource.data.calendar_days.length} attendance days` : 'Month overview'}</Badge></Column><IconButton icon="options-outline" label={jump ? 'Hide month selector' : 'Jump to month and year'} onPress={() => setJump(!jump)} /></Row>
      </View>
      {jump && <View style={{ padding: 16, gap: 12 }}><Field label="Year" value={year} onChangeText={setYear} keyboardType="number-pad" /><Field label="Month (1–12)" value={month} onChangeText={setMonth} keyboardType="number-pad" /><Button title="Go to month" variant="secondary" disabled={busy} onPress={() => void action.run(async () => {
        if (!/^\d{4}$/.test(year) || +year < 1 || +year > 9998 || !/^\d{1,2}$/.test(month) || +month < 1 || +month > 12) throw new Error('Invalid month or year.');
        setDay(undefined); setDate(''); setPeriod({ year, month }); setJump(false);
      })} /></View>}
      <View style={{ flexDirection: 'row' }}>{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((label, i) => <View key={label} style={{ width: '14.285714%', paddingVertical: 8 }}><Text style={{ textAlign: 'center', color: i > 4 ? c.coral : c.muted, ...typography.caption, fontWeight: '600' }}>{label}</Text></View>)}</View>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>{monthCells(+period.year, +period.month).map((key, i) => {
        const item = key ? records.get(key) : undefined; const selected = key === date; const current = key === dateKey(today);
        return <View key={key || `empty-${i}`} style={{ width: '14.285714%' }}>{key && <Pressable accessibilityRole="button" accessibilityLabel={`${key}${current ? ', today' : ''}, ${item ? `Attendance recorded` : 'no attendance recorded'}`} accessibilityState={{ selected, disabled: busy }} disabled={busy} onPress={() => { setDate(key); void loadDay(key); }} style={({ pressed }) => ({ marginVertical: 2, minHeight: sizing.compactTouch, paddingVertical: 8, gap: 4, borderRadius: sizing.smallRadius, borderWidth: current ? 1 : 0, borderColor: c.primary, backgroundColor: selected ? c.primary : item ? c.tealSoft : pressed ? c.soft : 'transparent', alignItems: 'center', justifyContent: 'center', opacity: busy ? 0.55 : 1 })}>
          <Text style={{ ...typography.body, fontWeight: selected || current ? '600' : '400', color: selected ? c.onPrimary : i % 7 > 4 ? c.coral : c.ink }}>{+key.slice(-2)}</Text>
          <View style={{ height: 4, flexDirection: 'row', gap: 4 }}>{item && Array.from({ length: Math.min(item.employee_count, 3) }, (_, j) => <View key={j} style={{ width: 4, height: 4, borderRadius: 2, backgroundColor: selected ? c.onPrimary : c.teal }} />)}</View>
        </Pressable>}</View>;
      })}</View>
      <View style={{ padding: 12, gap: 8 }}><Caption>Today · Attendance · Selected</Caption><Caption>Dots mark attendance.</Caption></View>
    </Card>
    <ErrorText error={resource.error || action.error} />{resource.loading && <Loading />}
    {resource.error && <Button title="Retry month" icon="refresh-outline" variant="secondary" onPress={() => void resource.refresh()} />}
    {resource.data?.calendar_days.length === 0 && <EmptyState icon="calendar-outline" title="A quiet month so far" message="No attendance." />}
    <Section title={date ? `Day details · ${date}` : 'Take a closer look'} detail={selectedRecord ? `${hours(selectedRecord.total_worked_seconds)} worked` : 'Select a date.'} />
    {selectedRecord && <LoginSourceBadges {...selectedRecord} />}
    <Card><Field label="Specific date" placeholder="YYYY-MM-DD" icon="calendar-outline" value={date} onChangeText={setDate} /><Button title={action.busy ? 'Loading day…' : 'View attendance'} variant="secondary" loading={action.busy} onPress={() => void loadDay(date)} /></Card>
    {day && <><Row><Column><Label>{day.date}</Label><Body>Total worked: {day.total_worked}</Body></Column><Badge>{day.employees.length ? 'Attendance recorded' : 'No attendance'}</Badge></Row>
      {day.employees.length === 0 && <EmptyState icon="sunny-outline" title="No attendance recorded" message="No attendance." />}
      {day.employees.map(person => <View key={person.employee_id} style={{ gap: 12 }}><Row><Avatar name={person.name} tone="teal" /><Column><Label>{person.name}</Label><Body>{person.worked_hours} worked</Body></Column></Row><LoginSourceBadges {...person} />{person.sessions ? person.sessions.map(session => <SessionCard key={session.id} session={session} showDuration />) : <Card><Badge tone={person.is_active ? 'teal' : 'primary'}>{person.is_active ? 'Active' : 'Completed'}</Badge><Body>Check in · {clockTime(person.login_at)}{'\n'}Check out · {person.logout_at ? clockTime(person.logout_at) : 'Awaiting checkout'}</Body></Card>}</View>)}</>}
    <Button title={busy ? 'Refreshing…' : 'Refresh calendar'} icon="refresh-outline" variant="secondary" loading={busy} disabled={busy} onPress={() => void action.run(async () => {
      await resource.refresh();
      if (date && dateValid(date)) { setDay(undefined); setDay(await api!.get<Day>(`calendar/day/?date=${date}&source=${source}`)); }
    })} />
  </Screen>;
}

import { useCallback, useState } from 'react';
import { FlatList, View, useWindowDimensions } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../../session';
import { EmployeeRow } from '../../types';
import { Avatar, Badge, Body, Button, Card, Caption, Column, EmptyState, ErrorText, Field, Label, Loading, Row, Section, stamp, useResource } from '../../ui';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { pageGutter, sizing, spacing } from '../../design';
import { useTheme } from '../../theme';
export default function Employees() {
  const { api } = useSession();
  const { colors: c } = useTheme();
  const { width } = useWindowDimensions(); const insets = useSafeAreaInsets();
  const gutter = pageGutter(width - insets.left - insets.right);
  const [search, setSearch] = useState('');
  const resource = useResource(useCallback(() => api!.get<{ employee_data: EmployeeRow[] }>('employees/'), [api]));
  const rows = (resource.data?.employee_data || []).filter(row => `${row.employee.name} ${row.employee.employee_id}`.toLowerCase().includes(search.toLowerCase()));
  return <FlatList showsVerticalScrollIndicator={false} style={{ backgroundColor: c.background }} contentContainerStyle={{ padding: spacing.lg, paddingLeft: gutter + insets.left, paddingRight: gutter + insets.right, paddingBottom: spacing.lg + insets.bottom, gap: spacing.md, flexGrow: 1, width: '100%', maxWidth: sizing.contentWidth, alignSelf: 'center' }} data={rows} keyExtractor={row => String(row.employee.id)} keyboardShouldPersistTaps="handled" automaticallyAdjustKeyboardInsets
    refreshing={resource.loading} onRefresh={() => void resource.refresh()}
    ListHeaderComponent={<View style={{ gap: 12 }}><Section title="Good people. Great team." detail="Attendance history and employee details, together." /><Button title="Add team member" icon="person-add-outline" onPress={() => router.push('/employee/create')} /><Field label="Find a team member" icon="search-outline" placeholder="Search name or employee ID" value={search} onChangeText={setSearch} /><Row><Column><Label>Team directory</Label></Column>{resource.data && <Badge>{rows.length} people</Badge>}</Row><ErrorText error={resource.error} /></View>}
    ListEmptyComponent={resource.loading ? <Loading /> : <EmptyState icon="people-outline" title={resource.error ? 'Your team couldn’t load' : search ? 'No matching team members' : 'Build your team'} message={resource.error ? 'Pull down to try again.' : search ? 'Try another name or employee ID.' : 'Add your first employee to get started.'} />}
    renderItem={({ item, index }) => <Card><Row><Avatar name={item.employee.name} tone={index % 2 ? 'teal' : 'primary'} /><Column><Label>{item.employee.name}</Label><Caption>{item.employee.employee_id} · Fingerprint {item.employee.fingerprint_id}</Caption></Column></Row><Badge tone={item.last_action === 'Login' ? 'teal' : item.last_action === 'Logout' ? 'primary' : 'amber'}>{item.last_action}</Badge><Body>{stamp(item.last_time)}</Body><Button title="View attendance" variant="secondary" icon="arrow-forward-outline" onPress={() => router.push({ pathname: '/employee/[id]', params: { id: item.employee.id } })} /></Card>} />;
}

import { View } from 'react-native';
import { Badge, Chip } from './ui';

export type LoginSource = 'all' | 'app' | 'device';
export function LoginSourceFilter({ value, onChange, disabled = false }: { value: LoginSource; onChange: (value: LoginSource) => void; disabled?: boolean }) {
  return <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
    {([['all', 'All'], ['app', 'App logins'], ['device', 'Device logins']] as const).map(([source, title]) => <Chip key={source} title={title} selected={value === source} disabled={disabled} onPress={() => onChange(source)} />)}
  </View>;
}
export function LoginSourceBadges({ app_logins = 0, device_logins = 0 }: { app_logins?: number; device_logins?: number }) {
  return <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
    {app_logins > 0 && <Badge tone="teal">App logins: {app_logins}</Badge>}
    {device_logins > 0 && <Badge>Device logins: {device_logins}</Badge>}
  </View>;
}

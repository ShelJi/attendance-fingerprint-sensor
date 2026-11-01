import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { ActivityIndicator, useWindowDimensions, Image, Pressable, ScrollView, StyleSheet, Text, TextInput, View, type TextInputProps, type StyleProp, type ViewStyle, type ColorValue, type ImageSourcePropType } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { simpleError } from './messages';
import { light, useTheme, type Tone } from './theme';
import { pageGutter, sizing, spacing, typography } from './design';
export { dateValid, validateRange } from './dates';

export const colors = light;
export type IconName = React.ComponentProps<typeof Ionicons>['name'];
export const stamp = (value: string | null) => value ? new Date(value).toLocaleString(undefined, { hour12: true }) : '—';
export const hours = (seconds: number) => `${Math.floor(seconds / 3600)}h ${Math.floor(seconds % 3600 / 60)}m`;
export function duration(value: string | null) {
  if (!value) return '—';
  const match = /^P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?$/.exec(value);
  return match ? hours((+(match[1] || 0) * 24 + +(match[2] || 0)) * 3600 + +(match[3] || 0) * 60 + +(match[4] || 0)) : value;
}
export function Icon({ name, size = sizing.icon, color }: { name: IconName; size?: number; color?: ColorValue | null }) { const { colors: c } = useTheme(); return <Ionicons name={name} size={size} style={{ color: color || c.primary }} accessible={false} aria-hidden importantForAccessibility="no-hide-descendants" />; }
export function Screen({ children }: { children: ReactNode }) {
  const { colors: c } = useTheme(); const insets = useSafeAreaInsets(); const { width } = useWindowDimensions();
  return <ScrollView showsVerticalScrollIndicator={false} style={{ backgroundColor: c.background }} contentContainerStyle={{ flexGrow: 1, paddingLeft: insets.left, paddingRight: insets.right, paddingBottom: Math.max(insets.bottom, 16) }} keyboardShouldPersistTaps="handled" keyboardDismissMode="on-drag" automaticallyAdjustKeyboardInsets>
    <View style={[s.screen, { paddingHorizontal: pageGutter(width - insets.left - insets.right) }]}>{children}</View>
  </ScrollView>;
}
export function Title({ children }: { children: ReactNode }) { const { colors: c } = useTheme(); return <Text style={[s.title, { color: c.ink }]}>{children}</Text>; }
export function Section({ title, detail }: { title: string; detail?: string }) { const { colors: c } = useTheme(); return <View style={{ gap: 4 }}><Text accessibilityRole="header" style={{ ...typography.section, color: c.ink }}>{title}</Text>{detail && <Text style={{ ...typography.secondary, color: c.muted }}>{detail}</Text>}</View>; }
export function Card({ children, tone, style }: { children: ReactNode; tone?: Tone; style?: StyleProp<ViewStyle> }) { const { colors: c } = useTheme(); return <View style={[s.card, { backgroundColor: tone ? c[`${tone}Soft`] : c.surface, borderColor: tone ? c[`${tone}Soft`] : c.line, shadowColor: c.shadow }, style]}>{children}</View>; }
export function Label({ children }: { children: ReactNode }) { const { colors: c } = useTheme(); return <Text style={[s.label, { color: c.ink }]}>{children}</Text>; }
export function Body({ children }: { children: ReactNode }) { const { colors: c } = useTheme(); return <Text style={[s.body, { color: c.muted }]}>{children}</Text>; }
export function Caption({ children }: { children: ReactNode }) { const { colors: c } = useTheme(); return <Text style={{ ...typography.caption, color: c.muted }}>{children}</Text>; }
export function Row({ children }: { children: ReactNode }) { return <View style={s.row}>{children}</View>; }
export function Column({ children }: { children: ReactNode }) { return <View style={{ flex: 1, minWidth: 0, gap: 4 }}>{children}</View>; }
export function Divider() { const { colors: c } = useTheme(); return <View style={{ height: 1, backgroundColor: c.line }} />; }
export function Badge({ children, tone = 'primary' }: { children: ReactNode; tone?: Tone }) { const { colors: c } = useTheme(); return <View style={{ alignSelf: 'flex-start', borderRadius: spacing.sm, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, backgroundColor: c[`${tone}Soft`], flexShrink: 1 }}><Text style={{ ...typography.caption, fontWeight: '600', color: c[tone] }}>{children}</Text></View>; }
export function Avatar({ name, tone = 'primary' }: { name: string; tone?: Tone }) { const { colors: c } = useTheme(); return <View style={{ minHeight: sizing.avatar, minWidth: sizing.avatar, padding: spacing.xs, borderRadius: sizing.smallRadius, backgroundColor: c[`${tone}Soft`], alignItems: 'center', justifyContent: 'center' }}><Text style={{ ...typography.label, color: c[tone] }}>{name.trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase()}</Text></View>; }
export function IconTile({ name, tone = 'primary' }: { name: IconName; tone?: Tone }) { const { colors: c } = useTheme(); return <View style={{ width: sizing.tile, height: sizing.tile, borderRadius: sizing.smallRadius, backgroundColor: c[`${tone}Soft`], alignItems: 'center', justifyContent: 'center' }}><Icon name={name} size={sizing.icon} color={c[tone]} /></View>; }
export function ErrorText({ error }: { error: string }) { const { colors: c } = useTheme(); return error ? <View accessibilityRole="alert" style={{ padding: spacing.md, borderRadius: sizing.smallRadius, backgroundColor: c.coralSoft, flexDirection: 'row', gap: spacing.sm }}><Icon name="alert-circle-outline" color={c.error} /><Text style={{ ...typography.body, flex: 1, minWidth: 0, color: c.error }}>{simpleError(error)}</Text></View> : null; }
export function Field({ label, icon, style, ...props }: TextInputProps & { label: string; icon?: IconName }) {
  const { colors: c } = useTheme(); const [focused, setFocused] = useState(false);
  return <View style={{ gap: spacing.xs }}><Label>{label}</Label><View style={[s.inputWrap, { borderColor: focused ? c.primary : c.line, backgroundColor: c.surface }]}>
    {icon && <Icon name={icon} color={focused ? c.primary : c.muted} />}<TextInput accessibilityLabel={label} placeholderTextColor={c.muted} style={[s.input, { color: c.ink }, props.multiline && { minHeight: 96, textAlignVertical: 'top' }, style]} autoCapitalize="none" {...props} onFocus={event => { setFocused(true); props.onFocus?.(event); }} onBlur={event => { setFocused(false); props.onBlur?.(event); }} />
  </View></View>;
}
export function Button({ title, onPress, disabled = false, danger = false, variant = 'primary', icon, loading = false }: { title: string; onPress: () => void; disabled?: boolean; danger?: boolean; variant?: 'primary' | 'secondary' | 'ghost'; icon?: IconName; loading?: boolean }) {
  const { colors: c, isDark } = useTheme(); const muted = variant !== 'primary'; const foreground = danger ? (muted ? c.error : isDark ? c.background : '#FFFFFF') : muted ? c.primary : c.onPrimary;
  return <Pressable accessibilityRole="button" accessibilityLabel={title} accessibilityState={{ disabled: disabled || loading, busy: loading }} disabled={disabled || loading} onPress={onPress} style={({ pressed }) => [s.button, { backgroundColor: danger ? (muted ? c.coralSoft : c.error) : variant === 'primary' ? c.primary : variant === 'secondary' ? c.primarySoft : 'transparent', opacity: disabled || loading ? 0.5 : pressed ? 0.8 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] }]}>
    {loading ? <ActivityIndicator size="small" color={foreground} /> : icon && <Icon name={icon} color={foreground} />}<Text style={[s.buttonText, { color: foreground }]}>{title}</Text>
  </Pressable>;
}
export function IconButton({ icon, label, onPress, disabled = false }: { icon: IconName; label: string; onPress: () => void; disabled?: boolean }) {
  const { colors: c } = useTheme(); return <Pressable accessibilityLabel={label} accessibilityRole="button" disabled={disabled} accessibilityState={{ disabled }} onPress={onPress} style={({ pressed }) => ({ minWidth: sizing.compactTouch, minHeight: sizing.compactTouch, padding: spacing.md, borderRadius: sizing.smallRadius, alignItems: 'center', justifyContent: 'center', backgroundColor: pressed ? c.primarySoft : c.surface, opacity: disabled ? 0.35 : 1 })}><Icon name={icon} /></Pressable>;
}
export function Chip({ title, selected, onPress, disabled = false, tone = 'primary', icon }: { title: string; selected: boolean; onPress: () => void; disabled?: boolean; tone?: Tone; icon?: IconName }) {
  const { colors: c } = useTheme(); return <Pressable accessibilityRole="button" accessibilityState={{ selected, disabled }} onPress={onPress} disabled={disabled} style={({ pressed }) => ({ minHeight: sizing.compactTouch, maxWidth: '100%', flexShrink: 1, borderRadius: sizing.smallRadius, borderWidth: 1, borderColor: selected ? c[tone] : c.line, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: selected ? c[`${tone}Soft`] : c.surface, opacity: disabled ? 0.45 : pressed ? 0.7 : 1 })}>{icon && <Icon name={icon} color={selected ? c[tone] : c.muted} />}<Text style={{ ...typography.body, fontWeight: selected ? '600' : '400', color: selected ? c[tone] : c.muted, flexShrink: 1 }}>{title}</Text>{selected && <Icon name="checkmark-circle" color={c[tone]} size={16} />}</Pressable>;
}
export function Hero({ eyebrow, title, subtitle, icon = 'finger-print-outline', logo, children }: { eyebrow: string; title: string; subtitle: string; icon?: IconName; logo?: ImageSourcePropType; children?: ReactNode }) {
  return <LinearGradient colors={['#6845D9', '#4258C9']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ borderRadius: sizing.radius, padding: spacing.lg, gap: spacing.md }}>
    <Row><View style={{ flex: 1, minWidth: 0 }}><Text style={{ color: '#EEE9FF', ...typography.caption, fontWeight: '600', letterSpacing: 1 }}>{eyebrow.toUpperCase()}</Text></View>{logo ? <Image source={logo} accessibilityLabel="PL attendance logo" resizeMode="contain" style={{ width: sizing.logo, height: sizing.logo, borderRadius: sizing.smallRadius, backgroundColor: '#F7F7F7' }} /> : <View style={{ padding: spacing.sm, borderRadius: sizing.smallRadius, backgroundColor: '#FFFFFF20' }}><Icon name={icon} size={sizing.icon} color="#FFFFFF" /></View>}</Row>
    <Text accessibilityRole="header" style={[s.title, { color: '#FFFFFF' }]}>{title}</Text><Text style={[s.body, { color: '#EFEBFF' }]}>{subtitle}</Text>{children}
  </LinearGradient>;
}
export function Stat({ label, value, icon, tone = 'primary' }: { label: string; value: string | number; icon: IconName; tone?: Tone }) { const { colors: c } = useTheme(); const { fontScale } = useWindowDimensions(); return <Card tone={tone} style={{ flexGrow: 1, flexShrink: 1, flexBasis: 136 * fontScale, minWidth: 0, padding: spacing.md, gap: spacing.sm }}><Row><Icon name={icon} color={c[tone]} size={sizing.icon} /><Text style={[typeof value === 'number' ? s.title : typography.section, { color: c.ink, fontVariant: ['tabular-nums'], flexShrink: 1, minWidth: 0 }]}>{value}</Text></Row><Body>{label}</Body></Card>; }
export function EmptyState({ title, message, icon = 'file-tray-outline' }: { title: string; message: string; icon?: IconName }) { return <Card style={{ alignItems: 'center', paddingVertical: spacing.xl }}><IconTile name={icon} /><Label>{title}</Label><Body>{message}</Body></Card>; }
export function Loading() { const { colors: c } = useTheme(); return <View accessibilityRole="progressbar" accessibilityLabel="Loading attendance data" style={{ gap: spacing.md, padding: spacing.lg, borderRadius: sizing.radius, backgroundColor: c.surface }}><ActivityIndicator color={c.primary} /><Body>Loading…</Body></View>; }
export function DateRange({ start, end, onStart, onEnd, onApply, disabled = false }: { start: string; end: string; onStart: (value: string) => void; onEnd: (value: string) => void; onApply: () => void; disabled?: boolean }) {
  const { fontScale } = useWindowDimensions();
  return <Card><Row><IconTile name="options-outline" /><Column><Label>Filter by date</Label><Caption>YYYY-MM-DD</Caption></Column></Row><View style={s.wrap}>
    <View style={[s.flexField, { flexBasis: 132 * fontScale }]}><Field label="From" placeholder="YYYY-MM-DD" value={start} onChangeText={onStart} keyboardType="numbers-and-punctuation" /></View><View style={[s.flexField, { flexBasis: 132 * fontScale }]}><Field label="To" placeholder="YYYY-MM-DD" value={end} onChangeText={onEnd} keyboardType="numbers-and-punctuation" /></View>
  </View><Button title="Apply dates" icon="filter-outline" variant="secondary" onPress={onApply} disabled={disabled} /></Card>;
}
export function useResource<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const version = useRef(0);
  const refresh = useCallback(async () => {
    const current = ++version.current;
    setLoading(true); setError(''); setData(undefined);
    try { const result = await load(); if (current === version.current) setData(result); }
    catch (e) { if (current === version.current) setError((e as Error).message); }
    finally { if (current === version.current) setLoading(false); }
  }, [load]);
  useFocusEffect(useCallback(() => { void refresh(); return () => { version.current++; }; }, [refresh]));
  return { data, error, loading, refresh };
}
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lock = useRef(false);
  useEffect(() => () => { lock.current = false; }, []);
  async function run(action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try { await action(); } catch (e) { setError((e as Error).message); }
    finally { lock.current = false; setBusy(false); }
  }
  return { busy, error, run };
}
const s = StyleSheet.create({
  screen: { padding: spacing.lg, gap: spacing.lg, width: '100%', maxWidth: sizing.contentWidth, alignSelf: 'center' },
  title: { ...typography.title, flexShrink: 1 },
  card: { padding: spacing.lg, borderRadius: sizing.radius, borderWidth: 1, gap: spacing.md, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 16, elevation: 1 },
  label: { ...typography.label, flexShrink: 1 },
  body: { ...typography.body, flexShrink: 1 },
  inputWrap: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: sizing.smallRadius, paddingHorizontal: spacing.md, minHeight: sizing.touch, gap: spacing.sm },
  input: { ...typography.input, flex: 1, minWidth: 0, paddingVertical: spacing.md, outlineWidth: 0 },
  button: { minHeight: sizing.touch, paddingHorizontal: spacing.md, paddingVertical: spacing.md, borderRadius: sizing.smallRadius, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: spacing.sm },
  buttonText: { ...typography.label, flexShrink: 1, textAlign: 'center' },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, minWidth: 0 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  flexField: { flexGrow: 1, flexShrink: 1, flexBasis: 132, minWidth: 0 },
});

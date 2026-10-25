import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Api, ApiError, serverUrl } from '../api';
import { attendanceMessage, type Attendance } from '../attendance';
import { captureVerification, type Position, type WorkMode } from '../verification';
import { AttendanceToast, useAttendanceAlerts } from '../notifications';

function Field({ label, ...props }: TextInputProps & { label: string }) {
  return <View style={s.field}><Text style={s.label}>{label}</Text><TextInput accessibilityLabel={label} autoCapitalize="none" autoCorrect={false} style={s.input} {...props} /></View>;
}
function Button({ title, onPress, disabled, secondary = false }: { title: string; onPress: () => void; disabled: boolean; secondary?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [s.button, secondary && s.secondary, { opacity: disabled ? 0.5 : pressed ? 0.8 : 1 }]}><Text style={[s.buttonText, secondary && s.secondaryText]}>{title}</Text></Pressable>;
}

export default function StaffAttendance() {
  const [server, setServer] = useState(process.env.EXPO_PUBLIC_API_URL || 'https://s.plsofttech.com');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [api, setApi] = useState<Api | null>(null);
  const [attendance, setAttendance] = useState<Attendance | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [mode, setMode] = useState<WorkMode>('office');
  const [place, setPlace] = useState('');
  const [description, setDescription] = useState('');
  const [position, setPosition] = useState<Position | null>(null);
  const [verificationStatus, setVerificationStatus] = useState('');
  const alerts = useAttendanceAlerts(api, 'me/notifications/');
  useEffect(() => {
    if (!api || !alerts.text) return;
    let active = true;
    api.get<Attendance>('me/attendance/').then(data => { if (active) setAttendance(data); }).catch(() => {});
    return () => { active = false; };
  }, [api, alerts.text]);
  function clearSession() {
    setApi(null); setAttendance(null); setPassword(''); setOldPassword('');
    setNewPassword(''); setConfirmPassword(''); setShowPassword(false);
    setPlace(''); setDescription(''); setPosition(null); setMode('office');
  }
  async function run(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError(''); setMessage('');
    try { await work(); }
    catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) clearSession();
      setError(reason instanceof Error ? reason.message : 'Something went wrong. Please try again.');
    } finally { setBusy(false); setVerificationStatus(''); }
  }
  async function signIn() {
    const origin = serverUrl(server);
    if (!__DEV__ && !origin.startsWith('https://')) throw new Error('Use an HTTPS server for release builds.');
    const client = new Api(origin);
    client.onUnauthorized = clearSession;
    await client.login(username.trim(), password);
    try {
      const data = await client.get<Attendance>('me/attendance/');
      if (!data.verification || !Array.isArray(data.evidence)) throw new Error('The backend needs the staff verification update. Ask your admin to deploy it and run migrations.');
      setAttendance(data); setApi(client); setPassword('');
    } catch (reason) {
      await client.logout().catch(() => {});
      throw reason;
    }
  }
  async function refresh() { setAttendance(await api!.get<Attendance>('me/attendance/')); }
  async function record() {
    try {
      if (mode === 'outdoor' && (!place.trim() || !description.trim())) throw new Error('Outdoor attendance needs a place name and description of today’s work.');
      if (mode === 'office' && !attendance!.verification.office_configured) throw new Error('Ask your admin to configure an active office location and Wi-Fi first.');
      setVerificationStatus(mode === 'office' ? 'Checking office Wi-Fi and GPS…' : 'Capturing your current GPS location…');
      const proof = await captureVerification(mode);
      setPosition(proof.location);
      const payload = { action: attendance!.checked_in ? 'logout' : 'login', mode, ...proof, ...(mode === 'outdoor' ? { place_name: place.trim(), work_description: description.trim() } : {}) };
      setVerificationStatus('Verifying and saving attendance…');
      const data = await api!.post<Attendance>('me/attendance/', payload);
      setAttendance(data); setMessage(attendanceMessage(data.action));
      if (data.notification_id && (data.action === 'login' || data.action === 'logout')) alerts.announce(data.notification_id, attendanceMessage(data.action));
    } catch (reason) {
      // Refresh after conflicts or network failures so a retry reflects server state.
      await refresh().catch(() => {});
      throw reason;
    }
  }
  const stamp = (value: string) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return <SafeAreaView style={s.safe}><KeyboardAvoidingView style={s.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <ScrollView contentContainerStyle={s.screen} keyboardShouldPersistTaps="handled" automaticallyAdjustKeyboardInsets>
      <View style={s.brandRow}><Image source={require('../../assets/pl-logo.jpg')} accessibilityLabel="PL attendance logo" resizeMode="contain" style={s.logo} /><View style={s.flex}><Text style={s.brand}>PL attendance</Text><Text style={s.body}>Your day. Accounted for.</Text></View></View>
      {!api || !attendance ? <>
        <Text accessibilityRole="header" style={s.title}>Your day starts here.</Text>
        <Text style={s.body}>Sign in to record your attendance.</Text>
        <View style={s.card}>
          <Field label="Server URL" value={server} onChangeText={setServer} keyboardType="url" editable={!busy} />
          <Field label="Username" value={username} onChangeText={setUsername} autoComplete="username" editable={!busy} />
          <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry autoComplete="current-password" editable={!busy} />
          <Button title="Sign in" disabled={busy || !username.trim() || !password} onPress={() => void run(signIn)} />
        </View>
        <Text style={s.body}>First time? Your employee ID is your username and initial password. Change your password after signing in.</Text>
      </> : <>
        <Text accessibilityRole="header" style={s.title}>Hello, {attendance.employee.name}.</Text>
        <Text style={s.body}>{attendance.username} · {new Date().toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })}</Text>
        <View style={s.hero}>
          <Text style={s.status}>{attendance.checked_in ? '●  CHECKED IN' : '○  CHECKED OUT'}</Text>
          <Text style={s.heroTitle}>{attendance.checked_in ? 'You’re on the clock.' : 'Ready when you are.'}</Text>
          <Text style={s.heroBody}>Attendance is saved using the server’s time. Allow five minutes between check-in and check-out.</Text>
        </View>
        <View style={s.card}><Text style={s.label}>WHERE ARE YOU WORKING?</Text><View style={s.row}>
          <View style={s.flex}><Button title={mode === 'office' ? '✓ In office' : 'In office'} secondary={mode !== 'office'} disabled={busy} onPress={() => { setMode('office'); setPosition(null); }} /></View>
          <View style={s.flex}><Button title={mode === 'outdoor' ? '✓ Outdoor' : 'Outdoor'} secondary={mode !== 'outdoor'} disabled={busy} onPress={() => { setMode('outdoor'); setPosition(null); }} /></View>
        </View>{mode === 'office' ? <Text style={s.body}>{attendance.verification?.office_configured ? 'Connect to your office Wi-Fi and enable precise location. Both must match the office configured by your admin.' : 'Your admin needs to configure the office Wi-Fi and location before office attendance can be recorded.'}</Text> : <>
          <Text style={s.body}>Describe where you are and today’s work. GPS is captured when you submit. No photo is needed.</Text>
          <Field label="Place name" placeholder="e.g. Client office, Kochi" value={place} onChangeText={setPlace} maxLength={200} editable={!busy} />
          <Field label="Today’s work description" placeholder="Describe the work you are doing today" value={description} onChangeText={setDescription} maxLength={4000} editable={!busy} multiline style={[s.input, s.description]} />
        </>}
        <Text style={s.body}>Location is collected only when you submit and is visible to your admin with your work details.</Text>
        {position && <Text style={s.body}>GPS: {position.latitude.toFixed(6)}, {position.longitude.toFixed(6)} · ±{Math.round(position.accuracy)} m</Text>}
        <Button title={attendance.checked_in ? 'Verify & check out' : 'Verify & check in'} disabled={busy || (mode === 'office' && !attendance.verification?.office_configured) || (mode === 'outdoor' && (!place.trim() || !description.trim()))} onPress={() => void run(record)} /></View>
        <Button title="Refresh attendance" secondary disabled={busy} onPress={() => void run(refresh)} />
        <View style={s.card}><Text style={s.label}>TODAY’S ACTIVITY</Text>
          {!attendance.sessions.length && <Text style={s.body}>No attendance yet. Check in to begin your day.</Text>}
          {attendance.sessions.map(item => <View key={item.id} style={s.row}><Text style={s.body}>In {stamp(item.login_at)}</Text><Text style={s.label}>{item.logout_at ? `Out ${stamp(item.logout_at)}` : 'In progress'}</Text></View>)}
          {attendance.evidence?.map(item => <View key={item.id} style={s.field}><Text style={s.label}>{item.action === 'login' ? 'Check in' : 'Check out'} · {item.mode === 'office' ? 'Office verified' : `Outdoor · ${item.place_name}`}</Text>{item.mode === 'outdoor' && <Text style={s.body}>{item.work_description}</Text>}</View>)}
        </View>
        <Button title={showPassword ? 'Close password settings' : 'Change password'} secondary disabled={busy} onPress={() => { setShowPassword(!showPassword); setOldPassword(''); setNewPassword(''); setConfirmPassword(''); }} />
        {showPassword && <View style={s.card}>
          <Field label="Current password" value={oldPassword} onChangeText={setOldPassword} secureTextEntry autoComplete="current-password" editable={!busy} />
          <Field label="New password" value={newPassword} onChangeText={setNewPassword} secureTextEntry autoComplete="new-password" editable={!busy} />
          <Field label="Confirm new password" value={confirmPassword} onChangeText={setConfirmPassword} secureTextEntry autoComplete="new-password" editable={!busy} />
          <Text style={s.body}>Use at least eight characters and avoid common passwords or your username.</Text>
          <Button title="Save password" disabled={busy || !oldPassword || !newPassword || !confirmPassword} onPress={() => void run(async () => {
            const data = await api.post<{ csrf_token: string }>('auth/password/', { old_password: oldPassword, new_password1: newPassword, new_password2: confirmPassword });
            api.csrf = data.csrf_token; setOldPassword(''); setNewPassword(''); setConfirmPassword(''); setShowPassword(false); setMessage('Password changed. You’re still signed in.');
          })} />
        </View>}
        <Button title="Sign out" secondary disabled={busy} onPress={() => void run(async () => { await api.logout(); clearSession(); })} />
      </>}
      {busy && <ActivityIndicator accessibilityLabel="Saving changes" color="#176B53" />}
      {!!verificationStatus && <Text accessibilityLiveRegion="polite" style={s.body}>{verificationStatus}</Text>}
      {!!error && <Text accessibilityRole="alert" style={s.error}>{error}</Text>}
      {!!message && <Text accessibilityLiveRegion="polite" style={s.message}>{message}</Text>}
    </ScrollView>
  </KeyboardAvoidingView><AttendanceToast text={alerts.text} onDismiss={alerts.dismiss} /></SafeAreaView>;
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F3F6F2' }, flex: { flex: 1 },
  screen: { flexGrow: 1, padding: 24, gap: 16, width: '100%', maxWidth: 600, alignSelf: 'center' },
  brand: { fontSize: 12, fontWeight: '600', letterSpacing: 2, color: '#176B53', marginVertical: 16 },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  logo: { height: 64, width: 64, borderRadius: 16, backgroundColor: '#F7F7F7' },
  description: { minHeight: 120, textAlignVertical: 'top' },
  title: { fontSize: 32, fontWeight: '600', color: '#18382E' },
  body: { fontSize: 16, color: '#52665D', lineHeight: 24 },
  card: { padding: 24, borderRadius: 24, backgroundColor: '#FFFFFF', gap: 16 },
  field: { gap: 8 }, label: { fontSize: 12, fontWeight: '600', color: '#304D40' },
  input: { minHeight: 48, borderWidth: 1, borderColor: '#CFDCD3', borderRadius: 12, padding: 12, fontSize: 16, color: '#18382E', backgroundColor: '#FFFFFF' },
  button: { minHeight: 56, borderRadius: 16, padding: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: '#176B53' },
  buttonText: { fontSize: 16, fontWeight: '600', color: '#FFFFFF' },
  secondary: { backgroundColor: '#E4EDE6' }, secondaryText: { color: '#176B53' },
  hero: { padding: 24, borderRadius: 24, gap: 16, backgroundColor: '#183E32', marginTop: 8 },
  status: { fontSize: 12, fontWeight: '600', color: '#BCEBCB', letterSpacing: 1 },
  heroTitle: { fontSize: 24, fontWeight: '600', color: '#FFFFFF' },
  heroBody: { fontSize: 16, lineHeight: 24, color: '#D4E5DA' },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 16, minHeight: 48 },
  error: { fontSize: 16, lineHeight: 24, color: '#A32929', padding: 16, backgroundColor: '#FDEDED', borderRadius: 12 },
  message: { fontSize: 16, lineHeight: 24, color: '#176B53', padding: 16, backgroundColor: '#DDEFE4', borderRadius: 12 },
});

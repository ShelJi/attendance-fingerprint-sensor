import { useState } from 'react';
import { Alert } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../session';
import { DEFAULT_BACKEND_URL } from '../settings';
import { serverUrl } from '../api';
import { Badge, Body, Button, Card, Column, ErrorText, Field, IconTile, Label, Row, Screen, Section, useAction } from '../ui';

export default function Settings() {
  const { api, username, saveServer } = useSession();
  const [origin, setOrigin] = useState(api?.origin || DEFAULT_BACKEND_URL);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [passwordSaved, setPasswordSaved] = useState(false);
  const passwordAction = useAction();
  const action = useAction();
  return <Screen><Section title="Your workspace, your way" detail="Manage the connection behind your attendance app." />
    <Card><Row><IconTile name="person-circle-outline" /><Column><Label>{username || 'Not signed in'}</Label><Body>{username ? 'Your attendance workspace' : 'Sign in to access your team'}</Body></Column></Row><Badge>Appearance · Follows your device</Badge></Card>
    {!username && <Button title="Back to sign in" variant="secondary" onPress={() => router.replace('/login')} />}
    <Section title="Backend connection" /><Card>
    <Field label="Backend URL" icon="globe-outline" value={origin} onChangeText={setOrigin} placeholder="http://192.168.1.20:8000" keyboardType="url" autoCorrect={false} />
    <Body>Enter only the server origin, without /web/dashboard or /api/mobile/. Changing servers returns you to sign in.</Body>
    <ErrorText error={action.error} /><Button title={action.busy ? 'Saving…' : 'Save backend URL'} icon="checkmark-outline" loading={action.busy} disabled={!origin.trim()} onPress={() => void action.run(async () => {
      await saveServer(origin);
      Alert.alert('Settings saved', 'The app will use this backend URL.');
      if (serverUrl(origin) !== api?.origin) router.replace('/login');
      else if (router.canGoBack()) router.back();
      else router.replace(username ? '/' : '/login');
    })} /></Card>
    {username && <Card><Section title="Change password" detail="Enter your current password and choose a new one." />
      <Field label="Current password" value={oldPassword} onChangeText={setOldPassword} secureTextEntry autoComplete="current-password" editable={!passwordAction.busy} />
      <Field label="New password" value={newPassword} onChangeText={setNewPassword} secureTextEntry autoComplete="new-password" editable={!passwordAction.busy} />
      <Field label="Confirm new password" value={confirmation} onChangeText={setConfirmation} secureTextEntry autoComplete="new-password" editable={!passwordAction.busy} />
      <ErrorText error={passwordAction.error} />{passwordSaved && <Body>Password updated. You are still signed in.</Body>}
      <Button title="Save password" loading={passwordAction.busy} disabled={!oldPassword || !newPassword || !confirmation} onPress={() => void passwordAction.run(async () => {
        setPasswordSaved(false);
        if (newPassword !== confirmation) throw new Error('The new passwords do not match.');
        const data = await api!.post<{ csrf_token: string }>('auth/password/', { old_password: oldPassword, new_password1: newPassword, new_password2: confirmation });
        api!.csrf = data.csrf_token;
        setOldPassword(''); setNewPassword(''); setConfirmation(''); setPasswordSaved(true);
      })} />
    </Card>}
    <Card tone="teal"><Row><IconTile name="shield-checkmark-outline" tone="teal" /><Column><Label>A private connection</Label><Body>Use HTTPS for your hosted server. Your password is never saved by the app.</Body></Column></Row></Card></Screen>;
}

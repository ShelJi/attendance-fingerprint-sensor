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
  const action = useAction();
  return <Screen><Section title="Your workspace, your way" detail="Manage the connection behind your attendance app." />
    <Card><Row><IconTile name="person-circle-outline" /><Column><Label>{username || 'Not signed in'}</Label><Body>{username ? 'Your attendance workspace' : 'Sign in to access your team'}</Body></Column></Row><Badge>Appearance · Follows your device</Badge></Card>
    <Section title="Backend connection" /><Card>
    <Field label="Backend URL" icon="globe-outline" value={origin} onChangeText={setOrigin} placeholder="https://s.plsofttech.com" keyboardType="url" autoCorrect={false} />
    <Body>Enter only the server origin, without /web/dashboard or /api/mobile/. Changing servers returns you to sign in.</Body>
    <ErrorText error={action.error} /><Button title={action.busy ? 'Saving…' : 'Save backend URL'} icon="checkmark-outline" loading={action.busy} disabled={!origin.trim()} onPress={() => void action.run(async () => {
      await saveServer(origin);
      Alert.alert('Settings saved', 'The app will use this backend URL.');
      if (serverUrl(origin) !== api?.origin) router.replace('/login');
      else router.back();
    })} /></Card><Card tone="teal"><Row><IconTile name="shield-checkmark-outline" tone="teal" /><Column><Label>A private connection</Label><Body>Use HTTPS for your hosted server. Your password is never saved by the app.</Body></Column></Row></Card></Screen>;
}

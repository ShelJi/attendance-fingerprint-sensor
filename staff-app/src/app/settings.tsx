import { useState } from 'react';
import { router } from 'expo-router';
import { testNotification } from '../notifications';
import { useSession } from '../session';
import { Badge, Body, Button, Card, Column, ErrorText, Field, IconTile, Label, Row, Screen, Section, useAction } from '../ui';

export default function Settings() {
  const { api, username } = useSession();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [passwordSaved, setPasswordSaved] = useState(false);
  const passwordAction = useAction();
  const notificationAction = useAction();
  const [notificationStatus, setNotificationStatus] = useState('');
  return <Screen><Section title="Account" />
    <Card><Row><IconTile name="person-circle-outline" /><Column><Label>{username || 'Not signed in'}</Label><Body>{username ? 'Signed in' : 'Sign in.'}</Body></Column></Row><Badge>Appearance · Automatic</Badge></Card>
    {!username && <Button title="Back to sign in" variant="secondary" onPress={() => router.replace('/login')} />}
    {username && <Card><Section title="Notifications" />
      <Body>Always enabled.</Body>
      <Button title="Test notification" icon="notifications-outline" loading={notificationAction.busy} onPress={() => void notificationAction.run(async () => {
        setNotificationStatus('');
        setNotificationStatus(await testNotification(api!, () => setNotificationStatus('Sent.')));
      })} />
      {!!notificationStatus && <Body>{notificationStatus}</Body>}
      <ErrorText error={notificationAction.error} />
    </Card>}
    {username && <Card><Section title="Change password" />
      <Field label="Current password" value={oldPassword} onChangeText={setOldPassword} secureTextEntry autoComplete="current-password" editable={!passwordAction.busy} />
      <Field label="New password" value={newPassword} onChangeText={setNewPassword} secureTextEntry autoComplete="new-password" editable={!passwordAction.busy} />
      <Field label="Confirm new password" value={confirmation} onChangeText={setConfirmation} secureTextEntry autoComplete="new-password" editable={!passwordAction.busy} />
      <ErrorText error={passwordAction.error} />{passwordSaved && <Body>Password updated.</Body>}
      <Button title="Save password" loading={passwordAction.busy} disabled={!oldPassword || !newPassword || !confirmation} onPress={() => void passwordAction.run(async () => {
        setPasswordSaved(false);
        if (newPassword !== confirmation) throw new Error('Passwords do not match.');
        const data = await api!.post<{ csrf_token: string }>('auth/password/', { old_password: oldPassword, new_password1: newPassword, new_password2: confirmation });
        api!.csrf = data.csrf_token;
        setOldPassword(''); setNewPassword(''); setConfirmation(''); setPasswordSaved(true);
      })} />
    </Card>}
    <Card tone="teal"><Row><IconTile name="shield-checkmark-outline" tone="teal" /><Column><Label>A private connection</Label><Body>Password not saved.</Body></Column></Row></Card></Screen>;
}

import { useState } from 'react';
import { useSession } from '../session';
import { Body, Button, Card, Caption, ErrorText, Field, Hero, Icon, Row, Screen, Section, useAction } from '../ui';

export default function Login() {
  const { api, connect } = useSession();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const action = useAction();
  return <Screen>
    <Hero logo={require('../../assets/pl-logo.jpg')} eyebrow="Your team. In sync." title={'A little clarity.\nEvery workday.'} subtitle="Your people, attendance, and daily insights. All in one place." />
    <Card><Section title="Welcome back" detail="Sign in to your attendance workspace." />
      <Field label="Username" icon="person-outline" placeholder="Your username" value={username} onChangeText={setUsername} autoComplete="username" autoCorrect={false} />
      <Field label="Password" icon="lock-closed-outline" placeholder="Your password" value={password} onChangeText={setPassword} secureTextEntry={!visible} autoComplete="current-password" />
      <Button title={visible ? 'Hide password' : 'Show password'} icon={visible ? 'eye-off-outline' : 'eye-outline'} variant="ghost" onPress={() => setVisible(!visible)} />
      <ErrorText error={action.error} /><Button title={action.busy ? 'Signing in…' : 'Sign in'} icon="arrow-forward-outline" loading={action.busy} disabled={!username.trim() || !password || !api} onPress={() => void action.run(async () => {
        await connect(username.trim(), password); setPassword('');
      })} />
    </Card><Row><Icon name="shield-checkmark-outline" /><Caption>Your password is never saved on this device.</Caption></Row><Body>Your login is remembered until you sign out or your session expires.</Body>
  </Screen>;
}

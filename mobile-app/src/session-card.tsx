import { Linking } from 'react-native';
import { Session } from './types';
import { googleMapsUrl } from './location';
import { Badge, Body, Button, Card, Caption, ErrorText, Label, Row, duration, stamp, useAction } from './ui';

export function SessionCard({ session, showDuration = false }: { session: Session; showDuration?: boolean }) {
  const action = useAction();
  const evidence = session.evidence || [];
  const appLogin = evidence.some(item => item.action === 'login');
  return <Card tone={appLogin ? 'teal' : undefined}>
    <Row><Badge tone={appLogin ? 'teal' : 'primary'}>{appLogin ? 'App' : 'Fingerprint'}</Badge><Badge tone={session.logout_at ? 'primary' : 'teal'}>{session.logout_at ? 'Completed' : 'Active'}</Badge></Row>
    {showDuration && <><Label>{duration(session.worked_hours)} worked</Label><Caption>Session #{session.id}</Caption></>}
    <Body>In · {stamp(session.login_at)}{'\n'}Out · {session.logout_at ? stamp(session.logout_at) : 'Awaiting checkout'}</Body>
    {(['login', 'logout'] as const).map(kind => {
      const proof = evidence.find(item => item.action === kind);
      if (!proof) return null;
      return <Button key={kind} title={kind === 'login' ? 'Check-in location' : 'Check-out location'} icon="location-outline" variant="secondary" onPress={() => void action.run(async () => { await Linking.openURL(googleMapsUrl(proof.latitude, proof.longitude)); })} />;
    })}
    <ErrorText error={action.error} />
  </Card>;
}

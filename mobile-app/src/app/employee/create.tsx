import { useState } from 'react';
import { Alert } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../../session';
import { Body, Button, Card, ErrorText, Field, Hero, IconTile, Row, Column, Label, Screen, useAction } from '../../ui';
export default function Create() {
  const { api } = useSession();
  const [name, setName] = useState(''); const [id, setId] = useState(''); const [finger, setFinger] = useState('');
  const action = useAction();
  return <Screen><Hero eyebrow="Grow your team" title="A new face. A fresh start." subtitle="Add their details to keep attendance connected." icon="person-add-outline" /><Card>
    <Field label="Full name" icon="person-outline" placeholder="e.g. Alex Morgan" value={name} onChangeText={setName} autoCapitalize="words" autoComplete="name" />
    <Field label="Employee ID" icon="id-card-outline" placeholder="e.g. EMP-001" value={id} onChangeText={setId} />
    <Field label="Fingerprint ID" icon="finger-print-outline" placeholder="Assigned sensor ID" value={finger} onChangeText={setFinger} />
    <ErrorText error={action.error} /><Button title={action.busy ? 'Saving…' : 'Create employee'} icon="checkmark-circle-outline" loading={action.busy} disabled={!name.trim() || !id.trim() || !finger.trim()} onPress={() => void action.run(async () => {
      await api!.post('employees/create/', { name: name.trim(), employee_id: id.trim(), fingerprint_id: finger.trim() });
      Alert.alert('Employee created'); router.back();
    })} /></Card><Card tone="teal"><Row><IconTile name="finger-print-outline" tone="teal" /><Column><Label>One more connection</Label><Body>Use the assigned fingerprint ID. Complete sensor enrollment from the Device tab.</Body></Column></Row></Card></Screen>;
}

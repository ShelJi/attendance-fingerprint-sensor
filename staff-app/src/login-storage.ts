import * as SecureStore from 'expo-secure-store';

export type SavedLogin = { origin: string; sessionKey: string };
const key = 'attendance-staff-login';
export async function readLogin(): Promise<SavedLogin | null> {
  const value = await SecureStore.getItemAsync(key);
  if (!value) return null;
  try {
    const saved = JSON.parse(value);
    return typeof saved.origin === 'string' && typeof saved.sessionKey === 'string' ? saved : null;
  } catch { return null; }
}
export async function writeLogin(value: SavedLogin | null) {
  if (value) await SecureStore.setItemAsync(key, JSON.stringify(value));
  else await SecureStore.deleteItemAsync(key);
}

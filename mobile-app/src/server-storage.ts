import * as SecureStore from 'expo-secure-store';
export const readServer = () => SecureStore.getItemAsync('attendance-server');
export const writeServer = (origin: string) => SecureStore.setItemAsync('attendance-server', origin);

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Platform } from 'react-native';
import { readLogin, writeLogin } from './login-storage';
import { Api, ApiError, serverUrl } from './api';
import { DEFAULT_BACKEND_URL } from './settings';

type Auth = { api: Api | null; username: string | null; ready: boolean; connect: (username: string, password: string) => Promise<void>; signOut: () => Promise<void> };
const Context = createContext<Auth>(null!);
export const useSession = () => useContext(Context);

function createClient() {
  const client = new Api(serverUrl(DEFAULT_BACKEND_URL));
  if (Platform.OS !== 'web') {
    client.sessionKey = null;
    client.onSessionChange = sessionKey => writeLogin(sessionKey ? { origin: client.origin, sessionKey } : null);
  }
  return client;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [api, setApi] = useState<Api | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const activeClient = useRef<Api | null>(null);
  function attach(client: Api) {
    activeClient.current = client;
    client.onUnauthorized = () => { if (activeClient.current === client) setUsername(null); };
    setApi(client);
  }
  useEffect(() => {
    (async () => {
      try {
        const client = createClient();
        attach(client);
        const saved = await readLogin();
        if (saved && saved.origin === client.origin && Platform.OS !== 'web') client.sessionKey = saved.sessionKey;
        else if (saved) await writeLogin(null);
        const session = await client.session();
        if (session.authenticated) {
          try { await client.requireStaff(); }
          catch (error) { if (error instanceof ApiError && [401, 403].includes(error.status)) throw error; }
          setUsername(session.username);
        }
      } catch { /* Keep the configured client available when its server is offline. */ }
      finally { setReady(true); }
    })();
  }, []);
  async function connect(user: string, password: string) {
    const client = createClient();
    const name = await client.login(user, password);
    try { await client.requireStaff(); }
    catch (error) { await client.logout().catch(() => {}); await writeLogin(null); throw error; }
    attach(client); setUsername(name);
  }
  async function signOut() { await api!.logout(); setUsername(null); }
  return <Context.Provider value={{ api, username, ready, connect, signOut }}>{children}</Context.Provider>;
}

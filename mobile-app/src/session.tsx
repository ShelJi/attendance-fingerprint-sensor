import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { readServer, writeServer } from './server-storage';
import { Api, ApiError, serverUrl } from './api';
import { configuredBackend } from './settings';

type Auth = { api: Api | null; username: string | null; ready: boolean; connect: (origin: string, username: string, password: string) => Promise<void>; signOut: () => Promise<void>; saveServer: (origin: string) => Promise<void> };
const Context = createContext<Auth>(null!);
export const useSession = () => useContext(Context);

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
        const origin = serverUrl(configuredBackend(await readServer()));
        if (origin) {
          const client = new Api(origin);
          attach(client);
          const session = await client.session();
          if (session.authenticated) {
            try { await client.requireManagement(); }
            catch (error) { if (error instanceof ApiError && [401, 403].includes(error.status)) throw error; }
            setUsername(session.username);
          }
        }
      } catch { /* Keep the configured client available when its server is offline. */ }
      finally { setReady(true); }
    })();
  }, []);
  async function connect(origin: string, user: string, password: string) {
    origin = serverUrl(origin);
    if (!__DEV__ && !origin.startsWith('https://')) throw new Error('Use an HTTPS server for release builds.');
    const client = new Api(origin);
    const name = await client.login(user, password);
    await client.requireManagement();
    await writeServer(origin);
    attach(client); setUsername(name);
  }
  async function signOut() { await api!.logout(); setUsername(null); }
  async function saveServer(value: string) {
    const origin = serverUrl(value);
    if (!__DEV__ && !origin.startsWith('https://')) throw new Error('Use an HTTPS server for release builds.');
    await writeServer(origin);
    if (origin !== api?.origin) { attach(new Api(origin)); setUsername(null); }
  }
  return <Context.Provider value={{ api, username, ready, connect, signOut, saveServer }}>{children}</Context.Provider>;
}

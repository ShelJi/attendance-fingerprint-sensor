import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Api } from './api';

type Notice = { id: number; name: string; action: string; occurred_at: string; mode: string };
export function useAttendanceAlerts(api: Api | null, path: string) {
  const [queue, setQueue] = useState<{ id: number; text: string; owner: Api }[]>([]);
  const current = queue[0];
  const seen = useRef(new Set<number>());
  const announce = useCallback((id: number, text: string) => {
    if (!api || seen.current.has(id)) return;
    seen.current.add(id); setQueue(items => [...items, { id, text, owner: api }]);
  }, [api]);
  useEffect(() => {
    if (!api) return;
    let stopped = false; let loading = false; let cursor: number | null = null;
    let timer: ReturnType<typeof setTimeout>;
    seen.current = new Set();
    async function poll() {
      if (stopped || loading) return;
      if (AppState.currentState !== 'active') { timer = setTimeout(poll, 5000); return; }
      loading = true; let delay = 5000;
      try {
        const data = await api!.get<{ notifications: Notice[]; cursor: number; has_more: boolean }>(path + (cursor === null ? '' : `?after=${cursor}`));
        if (stopped) return;
        if (cursor === null) setQueue(items => items.filter(item => item.owner === api));
        for (const item of data.notifications) {
          if (cursor === null) { seen.current.add(item.id); continue; }
          announce(item.id, `${item.name} ${item.action === 'login' ? 'checked in' : 'checked out'} · ${new Date(item.occurred_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`);
        }
        cursor = data.cursor;
        if (data.has_more) delay = 100;
      } catch { /* The durable feed is retried when the connection returns. */ }
      finally { loading = false; if (!stopped) timer = setTimeout(poll, delay); }
    }
    void poll();
    const listener = AppState.addEventListener('change', state => { if (state === 'active') { clearTimeout(timer); void poll(); } });
    return () => { stopped = true; clearTimeout(timer); listener.remove(); };
  }, [api, path, announce]);
  useEffect(() => {
    if (!current) return;
    const timer = setTimeout(() => setQueue(items => items.slice(1)), 4500);
    return () => clearTimeout(timer);
  }, [current]);
  return { text: api && current?.owner === api ? current.text : undefined, announce, dismiss: () => setQueue(items => items.slice(1)) };
}

export function AttendanceToast({ text, onDismiss }: { text?: string; onDismiss: () => void }) {
  const insets = useSafeAreaInsets();
  if (!text) return null;
  return <View pointerEvents="box-none" style={{ position: 'absolute', top: insets.top + 8, left: 16, right: 16, zIndex: 1000, alignItems: 'center' }}><Pressable accessibilityRole="button" accessibilityLabel={`${text}. Dismiss notification`} onPress={onDismiss} style={{ width: '100%', maxWidth: 600, borderRadius: 16, padding: 20, backgroundColor: '#183E32', borderColor: '#62BB8B', borderWidth: 1 }}><Text accessibilityLiveRegion="polite" style={{ color: 'white', fontSize: 16, lineHeight: 24 }}>{text}</Text></Pressable></View>;
}

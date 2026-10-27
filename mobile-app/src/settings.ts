// Change this default when moving the backend. Saved in-app Settings take priority.
export const DEFAULT_BACKEND_URL = process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export function configuredBackend(saved: string | null) {
  return !saved || saved === 'https://s.plsofttech.com' ? DEFAULT_BACKEND_URL : saved;
}

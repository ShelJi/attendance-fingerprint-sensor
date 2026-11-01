// Expo embeds this value from the project's environment when bundling the app.
export const DEFAULT_BACKEND_URL = process.env.EXPO_PUBLIC_API_URL?.trim() || '';

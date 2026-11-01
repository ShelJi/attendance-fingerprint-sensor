module.exports = ({ config }) => {
  const backend = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (!backend) throw new Error('Set EXPO_PUBLIC_API_URL in staff-app/.env before building the app.');
  const url = new URL(backend);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new Error('EXPO_PUBLIC_API_URL must be a server origin, such as https://attendance.example.com');
  }
  return ({
  ...config,
  plugins: [...(config.plugins || []), ...(url.protocol === 'http:' ? ['./plugins/with-http-backend'] : [])],
  ios: {
    ...config.ios,
    ...(url.protocol === 'http:' ? { infoPlist: {
      ...config.ios?.infoPlist,
      NSAppTransportSecurity: { ...config.ios?.infoPlist?.NSAppTransportSecurity, NSAllowsArbitraryLoads: true },
    } } : {}),
  },
  extra: {
    ...config.extra,
    ...(process.env.EXPO_PUBLIC_EAS_PROJECT_ID ? { eas: { ...config.extra?.eas, projectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID } } : {}),
  },
  android: {
    ...config.android,
    ...(process.env.GOOGLE_SERVICES_JSON ? { googleServicesFile: process.env.GOOGLE_SERVICES_JSON } : {}),
  },
  });
};

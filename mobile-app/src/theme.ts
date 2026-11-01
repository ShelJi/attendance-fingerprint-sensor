import { useColorScheme } from 'react-native';

export const light = {
  background: '#F7F7FC', surface: '#FFFFFF', soft: '#F0F0FA', ink: '#20223B', muted: '#656780',
  primary: '#6444D8', primarySoft: '#EEE9FF', teal: '#087F80', tealSoft: '#DFF5F0',
  coral: '#B7475E', coralSoft: '#FFE9EE', amber: '#8A610E', amberSoft: '#FFF2CC',
  line: '#E4E4F0', error: '#B02C48', shadow: '#493A80', onPrimary: '#FFFFFF',
};
export const dark: typeof light = {
  background: '#11121E', surface: '#1C1D30', soft: '#25263D', ink: '#F2F0FF', muted: '#B2B3CE',
  primary: '#B6A0FF', primarySoft: '#342653', teal: '#79D9C4', tealSoft: '#183C3C',
  coral: '#FFADC0', coralSoft: '#482737', amber: '#F4CE77', amberSoft: '#41351F',
  line: '#34354D', error: '#FFADC0', shadow: '#080710', onPrimary: '#241640',
};
export const useTheme = () => { const isDark = useColorScheme() === 'dark'; return { colors: isDark ? dark : light, isDark }; };
export type Tone = 'primary' | 'teal' | 'coral' | 'amber';
export { spacing } from './design';

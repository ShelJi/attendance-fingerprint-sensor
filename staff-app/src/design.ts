export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const typography = {
  title: { fontSize: 24, lineHeight: 30, fontWeight: '600' },
  section: { fontSize: 18, lineHeight: 24, fontWeight: '600' },
  label: { fontSize: 14, lineHeight: 20, fontWeight: '600' },
  body: { fontSize: 14, lineHeight: 20 },
  secondary: { fontSize: 12, lineHeight: 18 },
  caption: { fontSize: 12, lineHeight: 16 },
  input: { fontSize: 16, lineHeight: 22 },
} as const;
export const sizing = { touch: 48, compactTouch: 44, icon: 20, avatar: 36, tile: 40, logo: 40, radius: 16, smallRadius: 12, contentWidth: 600 } as const;
export const pageGutter = (width: number) => width < 360 ? spacing.md : spacing.lg;
export const tabBarHeight = (fontScale: number) => Math.max(64, 48 + 16 * fontScale);

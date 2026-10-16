import { MD3LightTheme } from 'react-native-paper';

export const colors = {
  navy950: '#071A33', navy900: '#0B2447', navy800: '#123A66',
  blue700: '#1D5FA7', blue600: '#2474C6', blue100: '#DDEEFF',
  sky500: '#38BDF8', sky100: '#E0F5FF', background: '#F4F8FC',
  surface: '#FFFFFF', surfaceMuted: '#EAF1F8', border: '#CAD8E6',
  text: '#102A43', textMuted: '#5B7087', success: '#16845B',
  successContainer: '#DDF6EA', error: '#BA1A1A', errorContainer: '#FFDAD6',
  warning: '#A65F00', scrim: 'rgba(7, 26, 51, 0.48)',
} as const;

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32 } as const;
export const radius = { sm: 8, md: 12, lg: 16, xl: 24, pill: 999 } as const;
export const layout = { screenPadding: spacing.xl, sectionGap: spacing.xl, minTouchTarget: 48, contentMaxWidth: 720 } as const;

export const theme = {
  ...MD3LightTheme,
  roundness: radius.md,
  colors: {
    ...MD3LightTheme.colors,
    primary: colors.navy900, onPrimary: '#FFFFFF',
    primaryContainer: colors.blue100, onPrimaryContainer: colors.navy900,
    secondary: colors.blue600, onSecondary: '#FFFFFF',
    secondaryContainer: colors.sky100, onSecondaryContainer: colors.navy800,
    tertiary: colors.sky500,
    background: colors.background, onBackground: colors.text,
    surface: colors.surface, onSurface: colors.text,
    surfaceVariant: colors.surfaceMuted, onSurfaceVariant: colors.textMuted,
    outline: colors.border, outlineVariant: '#E0E9F2',
    error: colors.error, errorContainer: colors.errorContainer,
    elevation: {
      ...MD3LightTheme.colors.elevation,
      level0: 'transparent', level1: colors.surface, level2: colors.surface,
      level3: colors.surface, level4: colors.surface, level5: colors.surface,
    },
  },
};

import { BrandVariants, Theme, createDarkTheme } from '@fluentui/react-components';

/**
 * 16-shade Electric Cobalt Blue Brand Ramp (#0052FF base)
 */
export const cobaltBrandRamp: BrandVariants = {
  10: '#000b26',
  20: '#001440',
  30: '#001e66',
  40: '#00298a',
  50: '#0035b3',
  60: '#0042db',
  70: '#0052ff', // Base Cobalt
  80: '#1a66ff',
  90: '#337aff',
  100: '#4d8eff',
  110: '#66a3ff',
  120: '#80b8ff',
  130: '#99ccff',
  140: '#b3e0ff',
  150: '#ccf0ff',
  160: '#e6f7ff'
};

/**
 * High-level Cyber Theme Palette Constants
 */
export const THEME_COLORS = {
  midnightBlack: '#080B10',
  midnightSurface: 'rgba(13, 17, 26, 0.82)',
  midnightElevated: 'rgba(20, 27, 42, 0.90)',
  electricCobalt: '#0052FF',
  cobaltHover: '#1A66FF',
  cobaltGlow: 'rgba(0, 82, 255, 0.45)',
  acidLime: '#CCFF00',
  limeHover: '#D9FF33',
  limeGlow: 'rgba(204, 255, 0, 0.45)',
  textPrimary: '#F8FAFC',
  textSecondary: '#94A3B8'
} as const;

/**
 * Custom Fluent UI v9 Theme overriding default dark palette
 * with Midnight Black background, Electric Cobalt controls, and Acid Lime focus/accents.
 */
export const phenomCyberTheme: Theme = {
  ...createDarkTheme(cobaltBrandRamp),

  // Midnight Black Surfaces
  colorNeutralBackground1: '#080B10',
  colorNeutralBackground2: '#0D111A',
  colorNeutralBackground3: '#141B2A',
  colorNeutralBackground4: '#1A2338',
  colorNeutralBackground5: '#202B45',
  colorNeutralBackground6: '#283654',
  colorSubtleBackground: 'rgba(13, 17, 26, 0.65)',
  colorSubtleBackgroundHover: 'rgba(0, 82, 255, 0.15)',
  colorSubtleBackgroundPressed: 'rgba(0, 82, 255, 0.25)',

  // Brand Controls (Electric Cobalt)
  colorBrandBackground: '#0052FF',
  colorBrandBackgroundHover: '#1A66FF',
  colorBrandBackgroundPressed: '#0040CC',
  colorBrandBackgroundSelected: '#0052FF',
  colorBrandForeground1: '#337AFF',
  colorBrandForeground2: '#66A3FF',

  // Focus & High-Voltage Highlights (Acid Lime)
  colorStrokeFocus1: '#080B10',
  colorStrokeFocus2: '#CCFF00',

  // Status & Telemetry Indicators
  colorStatusSuccessBackground1: 'rgba(204, 255, 0, 0.15)',
  colorStatusSuccessForeground1: '#CCFF00',
  colorStatusSuccessBorder1: '#CCFF00',

  // Text Contrast
  colorNeutralForeground1: '#F8FAFC',
  colorNeutralForeground2: '#E2E8F0',
  colorNeutralForeground3: '#94A3B8',
  colorNeutralForeground4: '#64748B'
};

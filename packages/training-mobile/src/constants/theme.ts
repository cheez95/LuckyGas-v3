import { MD3LightTheme, MD3DarkTheme } from 'react-native-paper';

export const lightTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#FF6B35',
    secondary: '#4ECDC4',
    tertiary: '#FFE66D',
    error: '#FF5252',
    background: '#F5F5F5',
    surface: '#FFFFFF',
    surfaceVariant: '#F0F0F0',
    onSurface: '#333333',
    onSurfaceVariant: '#666666',
    outline: '#E0E0E0',
    
    // Custom colors
    success: '#4CAF50',
    warning: '#FFC107',
    info: '#2196F3',
    
    // Gas delivery specific
    gasBlue: '#1E88E5',
    gasOrange: '#FF6B35',
    deliveryGreen: '#66BB6A',
  },
  
  // Custom properties
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  
  typography: {
    displayLarge: {
      fontSize: 32,
      fontWeight: '700',
      lineHeight: 40,
    },
    displayMedium: {
      fontSize: 28,
      fontWeight: '600',
      lineHeight: 36,
    },
    displaySmall: {
      fontSize: 24,
      fontWeight: '600',
      lineHeight: 32,
    },
    headlineLarge: {
      fontSize: 20,
      fontWeight: '600',
      lineHeight: 28,
    },
    headlineMedium: {
      fontSize: 18,
      fontWeight: '600',
      lineHeight: 24,
    },
    headlineSmall: {
      fontSize: 16,
      fontWeight: '600',
      lineHeight: 22,
    },
    bodyLarge: {
      fontSize: 16,
      fontWeight: '400',
      lineHeight: 24,
    },
    bodyMedium: {
      fontSize: 14,
      fontWeight: '400',
      lineHeight: 20,
    },
    bodySmall: {
      fontSize: 12,
      fontWeight: '400',
      lineHeight: 16,
    },
    labelLarge: {
      fontSize: 14,
      fontWeight: '500',
      lineHeight: 20,
    },
    labelMedium: {
      fontSize: 12,
      fontWeight: '500',
      lineHeight: 16,
    },
    labelSmall: {
      fontSize: 11,
      fontWeight: '500',
      lineHeight: 14,
    },
  },
  
  roundness: 8,
};

export const darkTheme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: '#FF8A65',
    secondary: '#64CCC5',
    tertiary: '#FFE66D',
    error: '#FF5252',
    background: '#121212',
    surface: '#1E1E1E',
    surfaceVariant: '#2A2A2A',
    onSurface: '#E0E0E0',
    onSurfaceVariant: '#B0B0B0',
    outline: '#424242',
    
    // Custom colors
    success: '#66BB6A',
    warning: '#FFCA28',
    info: '#42A5F5',
    
    // Gas delivery specific
    gasBlue: '#42A5F5',
    gasOrange: '#FF8A65',
    deliveryGreen: '#81C784',
  },
  
  spacing: lightTheme.spacing,
  typography: lightTheme.typography,
  roundness: lightTheme.roundness,
};

export const theme = lightTheme;
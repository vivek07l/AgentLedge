import { createTheme } from '@mui/material';

export const theme = createTheme({
  palette: {
    mode: 'light',
    // Lamborghini-inspired palette
    primary: {
      main: '#171717', // Near-black primary
      light: '#292929',
      dark: '#0A0A0A',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#F6C900', // Lamborghini-inspired yellow
      light: '#FFD733',
      dark: '#D4A800',
      contrastText: '#171717',
    },
    success: {
      main: '#B7F000', // Acid green for verified/high-performance status
      light: '#CFFF33',
      dark: '#8EBD00',
      contrastText: '#171717',
    },
    background: {
      default: '#111111', // Deep charcoal background (Lamborghini-inspired)
      paper: '#FFFFFF',    // Crisp white cards
    },
    text: {
      primary: '#171717',  // High-contrast near-black
      secondary: '#5A5A52', // Technical charcoal
    },
    divider: '#292929',     // Charcoal industrial borders
    info: {
      main: '#171717',
      light: '#F5F2E9',
      contrastText: '#FFFFFF',
    },
  },
  typography: {
    fontFamily: '"Space Grotesk", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: {
      fontFamily: '"Space Grotesk", "Arial Black", -apple-system, sans-serif',
      fontSize: 'clamp(2.4rem, 5vw, 3.8rem)',
      fontWeight: 900,
      letterSpacing: '-0.03em',
      lineHeight: 1.05,
    },
    h2: {
      fontFamily: '"Space Grotesk", "Arial Black", -apple-system, sans-serif',
      fontSize: '2.2rem',
      fontWeight: 900,
      letterSpacing: '-0.025em',
      lineHeight: 1.1,
    },
    h3: {
      fontFamily: '"Space Grotesk", -apple-system, sans-serif',
      fontSize: '1.75rem',
      fontWeight: 850,
      letterSpacing: '-0.02em',
    },
    h4: {
      fontFamily: '"Space Grotesk", -apple-system, sans-serif',
      fontSize: '1.45rem',
      fontWeight: 800,
      letterSpacing: '-0.015em',
    },
    h5: {
      fontFamily: '"Space Grotesk", -apple-system, sans-serif',
      fontSize: '1.2rem',
      fontWeight: 800,
      letterSpacing: '-0.01em',
    },
    h6: {
      fontFamily: '"Space Grotesk", -apple-system, sans-serif',
      fontSize: '1.05rem',
      fontWeight: 800,
      letterSpacing: '-0.01em',
    },
    subtitle1: {
      fontWeight: 650,
      letterSpacing: '-0.01em',
    },
    subtitle2: {
      fontWeight: 700,
      letterSpacing: '-0.005em',
    },
    body1: {
      fontSize: '0.975rem',
      lineHeight: 1.6,
      letterSpacing: '-0.005em',
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.55,
    },
    button: {
      fontFamily: '"Space Grotesk", -apple-system, sans-serif',
      fontWeight: 800,
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
    },
    overline: {
      fontFamily: '"Space Grotesk", -apple-system, monospace',
      fontWeight: 800,
      letterSpacing: '0.12em',
      fontSize: '0.75rem',
    },
  },
  shape: { borderRadius: 0 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
      body: {
          background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(246,201,0,0.07) 0%, transparent 70%), #111111',
          backgroundColor: '#111111',
          color: '#FFFFFF',
          boxSizing: 'border-box',
          minHeight: '100vh',
        },
        '*:focus-visible': {
          outline: '3px solid #F6C900',
          outlineOffset: 2,
        },
        '::selection': {
          background: '#F6C900',
          color: '#171717',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'uppercase',
          borderRadius: 0,
          minHeight: 40,
          fontWeight: 800,
          letterSpacing: '0.04em',
          border: '1px solid #171717',
          boxShadow: '3px 3px 0 #171717',
          transition: 'all 0.12s ease',
          '&:hover': {
            transform: 'translate(-1px, -1px)',
            boxShadow: '4px 4px 0 #171717',
          },
          '&:active': {
            transform: 'translate(1px, 1px)',
            boxShadow: '1px 1px 0 #171717',
          },
        },
        containedPrimary: {
          backgroundColor: '#171717',
          color: '#FFFFFF',
          '&:hover': {
            backgroundColor: '#292929',
            boxShadow: '4px 4px 0 #F6C900',
          },
        },
        containedSecondary: {
          backgroundColor: '#F6C900',
          color: '#171717',
          borderColor: '#171717',
          '&:hover': {
            backgroundColor: '#FFD733',
            boxShadow: '4px 4px 0 #171717',
          },
        },
        outlined: {
          backgroundColor: '#FFFFFF',
          color: '#171717',
          borderColor: '#292929',
          '&:hover': {
            backgroundColor: '#F5F2E9',
            borderColor: '#171717',
            boxShadow: '4px 4px 0 #F6C900',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          backgroundImage: 'none',
          borderColor: '#292929',
          backgroundColor: '#FFFFFF',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          backgroundColor: '#FFFFFF',
          border: '1px solid #292929',
          boxShadow: '4px 4px 0 #171717',
          transition: 'transform 0.14s ease, box-shadow 0.14s ease',
          '&:hover': {
            boxShadow: '6px 6px 0 #F6C900',
            transform: 'translate(-2px, -2px)',
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          backgroundColor: '#FFFFFF',
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: '#292929',
            borderWidth: '1px',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#171717',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#171717',
            borderWidth: '2px',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          fontWeight: 750,
          border: '1px solid #292929',
          letterSpacing: '-0.01em',
        },
        colorPrimary: {
          backgroundColor: '#171717',
          color: '#FFFFFF',
        },
        colorSecondary: {
          backgroundColor: '#F6C900',
          color: '#171717',
          borderColor: '#171717',
        },
        colorSuccess: {
          backgroundColor: '#B7F000',
          color: '#171717',
          borderColor: '#171717',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#171717',
          color: '#FFFFFF',
          borderBottom: '2px solid #292929',
          boxShadow: '0 4px 0 rgba(23, 23, 23, 0.08)',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          border: '1px solid #292929',
          boxShadow: '3px 3px 0 #171717',
          fontWeight: 500,
        },
        standardSuccess: {
          backgroundColor: '#F0FED0',
          borderColor: '#8EBD00',
          color: '#171717',
          '& .MuiAlert-icon': { color: '#688C00' },
        },
        standardInfo: {
          backgroundColor: '#FFFFFF',
          borderColor: '#292929',
          color: '#171717',
          '& .MuiAlert-icon': { color: '#171717' },
        },
      },
    },
  },
});

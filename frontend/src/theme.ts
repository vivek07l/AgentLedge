import { createTheme } from '@mui/material';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#5b5bd6', light: '#7777ed', dark: '#4141aa' },
    secondary: { main: '#17a995', light: '#44c7b2', dark: '#087d70' },
    background: { default: '#f6f7fb', paper: '#ffffff' },
    text: { primary: '#171a2b', secondary: '#74798c' },
    divider: '#e9eaf1',
    success: { main: '#138a72' },
  },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontSize: 'clamp(2.2rem, 5vw, 3.55rem)', fontWeight: 760, letterSpacing: '-0.055em', lineHeight: 1.08 },
    h2: { fontSize: '2.15rem', fontWeight: 740, letterSpacing: '-0.04em' },
    h3: { fontSize: '1.7rem', fontWeight: 720, letterSpacing: '-0.035em' },
    h4: { fontSize: '1.45rem', fontWeight: 700, letterSpacing: '-0.025em' },
    h5: { fontSize: '1.12rem', fontWeight: 680, letterSpacing: '-0.015em' },
    h6: { fontSize: '1rem', fontWeight: 670 },
    button: { fontWeight: 650, letterSpacing: '-0.01em' },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundImage: 'radial-gradient(ellipse at 74% 0%, rgba(91,91,214,.055), transparent 36%)' },
        '*:focus-visible': { outline: '3px solid rgba(91,91,214,.32)', outlineOffset: 2 },
        '::selection': { background: 'rgba(91,91,214,.18)' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', borderRadius: 10, minHeight: 42, boxShadow: 'none' },
        containedPrimary: { backgroundImage: 'linear-gradient(135deg, #6666e6, #5151c8)', '&:hover': { boxShadow: '0 8px 20px rgba(81,81,200,.2)' } },
      },
    },
    MuiPaper: { styleOverrides: { root: { borderRadius: 16, backgroundImage: 'none' } } },
    MuiCard: { styleOverrides: { root: { borderRadius: 16, border: '1px solid #e9eaf1', boxShadow: '0 5px 24px rgba(27,31,65,.035)', transition: 'transform .18s ease, box-shadow .18s ease, border-color .18s ease', '&:hover': { borderColor: '#d6d7ef', boxShadow: '0 12px 34px rgba(27,31,65,.075)', transform: 'translateY(-2px)' } } } },
    MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 11, backgroundColor: '#fff' } } },
    MuiChip: { styleOverrides: { root: { borderRadius: 8, fontWeight: 600 } } },
  },
});

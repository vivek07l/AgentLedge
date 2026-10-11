import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  useTheme,
  useMediaQuery,
  Typography,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Store as StoreIcon,
  History as HistoryIcon,
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
  Handyman as ProviderIcon,
  ApprovalRounded as ApprovalIcon,
  PlayCircleOutlineRounded as SimulationIcon,
} from '@mui/icons-material';
import { useAuth } from '../../store/AuthContext';

const DRAWER_WIDTH = 240;

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard', requiresAuth: true },
    { text: 'Marketplace', icon: <StoreIcon />, path: '/marketplace', requiresAuth: false },
    { text: 'Simulation', icon: <SimulationIcon />, path: '/simulation', requiresAuth: false },
    { text: 'History', icon: <HistoryIcon />, path: '/history', requiresAuth: true },
    { text: 'Profile', icon: <PersonIcon />, path: '/profile', requiresAuth: true },
    ...(user ? [{ text: 'AgentsLedge Approvals', icon: <ApprovalIcon />, path: '/approvals', requiresAuth: true }] : []),
    ...(user?.is_admin ? [{ text: 'Admin Control', icon: <AdminIcon />, path: '/admin', requiresAuth: true }] : []),
    ...(user?.is_developer ? [{ text: 'Provider Listings', icon: <ProviderIcon />, path: '/provider/listings', requiresAuth: true }] : []),
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      onClose();
    }
  };

  const filteredMenuItems = menuItems.filter(
    (item) => !item.requiresAuth || (user && item.requiresAuth)
  );

  const drawer = (
    <Box sx={{ overflow: 'auto', py: 2 }}>
      <Box sx={{ px: 2.5, mb: 2 }}>
        <Typography
          variant="overline"
          sx={{
            color: '#706E66',
            fontWeight: 800,
            letterSpacing: '0.12em',
            fontSize: '0.7rem',
          }}
        >
          {"// NAVIGATION"}
        </Typography>
      </Box>
      <List disablePadding>
        {filteredMenuItems.map((item) => {
          const isSelected = location.pathname === item.path;
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                selected={isSelected}
                onClick={() => handleNavigation(item.path)}
                sx={{
                  mx: 1.5,
                  py: 1,
                  px: 1.75,
                  borderRadius: 0,
                  border: isSelected ? '1px solid #171717' : '1px solid transparent',
                  borderLeft: isSelected ? '4px solid #F6C900 !important' : '4px solid transparent',
                  bgcolor: isSelected ? '#171717 !important' : 'transparent',
                  color: isSelected ? '#FFFFFF' : '#171717',
                  boxShadow: isSelected ? '2px 2px 0 #F6C900' : 'none',
                  transition: 'all 0.12s ease',
                  '&:hover': {
                    bgcolor: isSelected ? '#171717' : '#EAE5D9',
                    borderLeft: '4px solid #F6C900',
                  },
                  '& .MuiListItemIcon-root': {
                    color: isSelected ? '#F6C900' : '#5A5A52',
                    minWidth: 38,
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{
                    fontWeight: isSelected ? 800 : 650,
                    fontSize: '0.9rem',
                    letterSpacing: '-0.01em',
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box
      component="nav"
      sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
    >
      {isMobile ? (
        <Drawer
          variant="temporary"
          open={isOpen}
          onClose={onClose}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
              borderRight: '2px solid #292929',
              bgcolor: '#F5F2E9',
              borderRadius: 0,
            },
          }}
        >
          {drawer}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
              borderRight: '2px solid #292929',
              bgcolor: '#F5F2E9',
              borderRadius: 0,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      )}
    </Box>
  );
};

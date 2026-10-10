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
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Store as StoreIcon,
  History as HistoryIcon,
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
  Handyman as ProviderIcon,
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
    { text: 'History', icon: <HistoryIcon />, path: '/history', requiresAuth: true },
    { text: 'Profile', icon: <PersonIcon />, path: '/profile', requiresAuth: true },
    ...(user?.is_admin ? [{ text: 'Admin', icon: <AdminIcon />, path: '/admin', requiresAuth: true }] : []),
    ...(user?.is_developer ? [{ text: 'My services', icon: <ProviderIcon />, path: '/provider/listings', requiresAuth: true }] : []),
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
    <Box sx={{ overflow: 'auto' }}>
      <List>
        {filteredMenuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
          <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
              sx={{ mx: 1, my: .35, borderRadius: 2, '&.Mui-selected': { bgcolor: 'rgba(91,91,214,.1)', color: 'primary.main', '& .MuiListItemIcon-root': { color: 'primary.main' } } }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
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
            keepMounted: true, // Better open performance on mobile
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
              borderRight: '1px solid',
              borderColor: 'divider',
              bgcolor: '#fbfbfe',
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
              borderRight: '1px solid',
              borderColor: 'divider',
              bgcolor: '#fbfbfe',
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

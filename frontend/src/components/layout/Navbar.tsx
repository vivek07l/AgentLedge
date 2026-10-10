import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AppBar,
  Box,
  Toolbar,
  IconButton,
  Typography,
  Button,
  Menu,
  MenuItem,
  Avatar,
  Tooltip,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  AccountCircle as AccountCircleIcon,
  Token as TokenIcon,
} from '@mui/icons-material';
import { useAuth } from '../../store/AuthContext';
import { PurchaseTokens } from '../tokens/PurchaseTokens';

interface NavbarProps {
  onMenuClick?: () => void;
  showMenuButton?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  onMenuClick,
  showMenuButton = false,
}) => {
  const navigate = useNavigate();
  const { token, user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [showPurchaseDialog, setShowPurchaseDialog] = React.useState(false);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleClose();
    logout();
    navigate('/');
  };

  const handleProfile = () => {
    handleClose();
    navigate('/profile');
  };

  const handleDashboard = () => {
    handleClose();
    navigate('/dashboard');
  };

  return (
    <>
      <AppBar
        position="sticky"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          bgcolor: 'rgba(255,255,255,.88)',
          color: 'text.primary',
          backdropFilter: 'blur(16px)',
          borderBottom: '1px solid',
          borderColor: 'divider',
          boxShadow: 'none',
        }}
      >
        <Toolbar sx={{ minHeight: '68px !important', maxWidth: 1600, width: '100%', mx: 'auto', px: { xs: 2, sm: 3 } }}>
          {showMenuButton && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={onMenuClick}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}

          <Typography
            variant="h6"
            noWrap
            component="div"
            sx={{ flexGrow: 1, cursor: 'pointer', fontWeight: 760, letterSpacing: '-.035em', display: 'flex', alignItems: 'center', gap: 1.1 }}
            onClick={() => navigate('/')}
          >
            <Box sx={{ width: 30, height: 30, borderRadius: '10px', display: 'grid', placeItems: 'center', color: 'white', fontSize: 15, fontWeight: 800, background: 'linear-gradient(145deg,#7777ed,#4d4dbb)', boxShadow: '0 5px 14px rgba(91,91,214,.25)' }}>L</Box>
            AgentLedge
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Button color="primary" onClick={() => navigate('/simulation')} sx={{ mr: { xs: .25, sm: 1 }, minWidth: 0, px: { xs: 1, sm: 1.5 } }}>Simulation</Button>
            {token && (
              <Tooltip title="Add simulated demo tokens">
                <Chip
                  icon={<TokenIcon />}
                  label={`${user?.token_balance || 0} demo tokens`}
                  color="secondary"
                  variant="outlined"
                  onClick={() => setShowPurchaseDialog(true)}
                  sx={{ mr: 2, cursor: 'pointer' }}
                />
              </Tooltip>
            )}

            {token ? (
              <>
                <Tooltip title="Account settings">
                  <IconButton
                    size="large"
                    aria-label="account of current user"
                    aria-controls="menu-appbar"
                    aria-haspopup="true"
                    onClick={handleMenu}
                    color="inherit"
                  >
                    {user?.username ? (
                      <Avatar sx={{ width: 32, height: 32 }}>
                        {user.username[0].toUpperCase()}
                      </Avatar>
                    ) : (
                      <AccountCircleIcon />
                    )}
                  </IconButton>
                </Tooltip>
                <Menu
                  id="menu-appbar"
                  anchorEl={anchorEl}
                  anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'right',
                  }}
                  keepMounted
                  transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right',
                  }}
                  open={Boolean(anchorEl)}
                  onClose={handleClose}
                >
                  <MenuItem onClick={handleDashboard}>Dashboard</MenuItem>
                  <MenuItem onClick={handleProfile}>Profile</MenuItem>
                  <MenuItem onClick={handleLogout}>Logout</MenuItem>
                </Menu>
              </>
            ) : (
              <>
                <Button
                  color="primary"
                  onClick={() => navigate('/auth/login')}
                  sx={{ ml: 1 }}
                >
                  Login
                </Button>
                <Button
                  color="primary"
                  onClick={() => navigate('/auth/register')}
                  sx={{ ml: 1 }}
                >
                  Register
                </Button>
              </>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <PurchaseTokens
        open={showPurchaseDialog}
        onClose={() => setShowPurchaseDialog(false)}
      />
    </>
  );
};

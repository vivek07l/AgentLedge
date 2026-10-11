import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
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
  StorefrontRounded,
  PlayCircleFilledRounded,
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
  const location = useLocation();
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

  const isMarketplace = location.pathname === '/marketplace' || location.pathname === '/';
  const isSimulation = location.pathname === '/simulation';

  return (
    <>
      <AppBar
        position="sticky"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          bgcolor: '#171717',
          color: '#FFFFFF',
          borderBottom: '2px solid #292929',
          boxShadow: '0 4px 0 rgba(23, 23, 23, 0.12)',
        }}
      >
        <Toolbar
          sx={{
            minHeight: '68px !important',
            maxWidth: 1600,
            width: '100%',
            mx: 'auto',
            px: { xs: 1, sm: 3 },
          }}
        >
          {showMenuButton && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={onMenuClick}
              sx={{ mr: { xs: 0.75, sm: 2 }, flexShrink: 0 }}
            >
              <MenuIcon />
            </IconButton>
          )}

          {/* Lamborghini-inspired emblem and confident branding */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: { xs: 0.75, sm: 1.5 },
              cursor: 'pointer',
              flexGrow: 1,
              minWidth: 0,
            }}
            onClick={() => navigate('/marketplace')}
          >
            <Box
              sx={{
                width: { xs: 30, sm: 36 },
                height: { xs: 30, sm: 36 },
                flexShrink: 0,
                display: 'grid',
                placeItems: 'center',
                color: '#171717',
                bgcolor: '#F6C900',
                border: '2px solid #292929',
                boxShadow: '2px 2px 0 #000000',
                fontWeight: 900,
                fontSize: 18,
                clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
                transition: 'transform 0.15s ease',
                '&:hover': { transform: 'scale(1.05)' },
              }}
            >
              A
            </Box>
            <Box>
              <Typography
                variant="h6"
                noWrap
                component="div"
                sx={{
                  fontWeight: 900,
                  fontSize: { xs: '1.05rem', sm: '1.25rem' },
                  letterSpacing: '-0.03em',
                  lineHeight: 1.05,
                  color: '#FFFFFF',
                  fontFamily: '"Space Grotesk", sans-serif',
                }}
              >
                AgentsLedge
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  display: { xs: 'none', sm: 'block' },
                  color: '#F6C900',
                  fontWeight: 800,
                  letterSpacing: '0.12em',
                  fontSize: '0.65rem',
                  textTransform: 'uppercase',
                  lineHeight: 1,
                }}
              >
                Agent Service Network
              </Typography>
            </Box>
          </Box>

          {/* Navigation Controls */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.5, sm: 1.5 }, flexShrink: 0 }}>
            <Button
              variant={isMarketplace ? 'contained' : 'outlined'}
              color="secondary"
              size="small"
              startIcon={<StorefrontRounded sx={{ fontSize: 18 }} />}
              onClick={() => navigate('/marketplace')}
              sx={{
                display: { xs: 'none', sm: 'inline-flex' },
                fontSize: '0.8rem',
                minWidth: 0,
                px: { xs: 1.25, sm: 2 },
                bgcolor: isMarketplace ? '#F6C900' : 'transparent',
                color: isMarketplace ? '#171717' : '#FFFFFF',
                borderColor: isMarketplace ? '#171717' : '#333333',
                boxShadow: isMarketplace ? '2px 2px 0 #000000' : 'none',
              }}
            >
              Marketplace
            </Button>
            <Button
              variant={isSimulation ? 'contained' : 'outlined'}
              color="secondary"
              size="small"
              startIcon={<PlayCircleFilledRounded sx={{ fontSize: 18, color: isSimulation ? '#171717' : '#B7F000' }} />}
              onClick={() => navigate('/simulation')}
              sx={{
                display: { xs: 'none', sm: 'inline-flex' },
                fontSize: '0.8rem',
                minWidth: 0,
                px: { xs: 1.25, sm: 2 },
                bgcolor: isSimulation ? '#F6C900' : 'transparent',
                color: isSimulation ? '#171717' : '#FFFFFF',
                borderColor: isSimulation ? '#171717' : '#333333',
                boxShadow: isSimulation ? '2px 2px 0 #000000' : 'none',
              }}
            >
              Simulation
            </Button>

            {token && (
              <Tooltip title="Add simulated demo tokens">
                <Chip
                  icon={<TokenIcon sx={{ color: '#171717 !important' }} />}
                  label={
                    <>
                      <Box component="span" sx={{ display: { xs: 'inline', sm: 'none' } }}>
                        {user?.token_balance || 0}
                      </Box>
                      <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                        {user?.token_balance || 0} demo tokens
                      </Box>
                    </>
                  }
                  aria-label={`${user?.token_balance || 0} demo tokens`}
                  onClick={() => setShowPurchaseDialog(true)}
                  sx={{
                    height: { xs: 30, sm: 32 },
                    '& .MuiChip-label': { px: { xs: 0.5, sm: 1 } },
                    bgcolor: '#F6C900',
                    color: '#171717',
                    fontWeight: 800,
                    border: '1px solid #171717',
                    boxShadow: '2px 2px 0 #000000',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: '#FFD733' },
                  }}
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
                    sx={{ p: 0.5 }}
                  >
                    {user?.username ? (
                      <Avatar
                        sx={{
                          width: 34,
                          height: 34,
                          bgcolor: '#292929',
                          color: '#F6C900',
                          border: '1px solid #F6C900',
                          fontWeight: 800,
                          fontSize: '0.9rem',
                          borderRadius: 0,
                        }}
                      >
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
                  PaperProps={{
                    sx: {
                      bgcolor: '#FFFFFF',
                      border: '2px solid #171717',
                      boxShadow: '4px 4px 0 #171717',
                      borderRadius: 0,
                      minWidth: 160,
                    },
                  }}
                >
                  <MenuItem onClick={handleDashboard} sx={{ fontWeight: 700, '&:hover': { bgcolor: '#F5F2E9' } }}>
                    Dashboard
                  </MenuItem>
                  <MenuItem onClick={handleProfile} sx={{ fontWeight: 700, '&:hover': { bgcolor: '#F5F2E9' } }}>
                    Profile
                  </MenuItem>
                  <MenuItem onClick={handleLogout} sx={{ fontWeight: 700, color: '#C01A1A', '&:hover': { bgcolor: '#F5F2E9' } }}>
                    Logout
                  </MenuItem>
                </Menu>
              </>
            ) : (
              <>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/auth/login')}
                  sx={{
                    ml: 0.5,
                    bgcolor: 'transparent',
                    color: '#FFFFFF',
                    borderColor: '#444444',
                    '&:hover': { borderColor: '#F6C900', color: '#F6C900' },
                  }}
                >
                  Login
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  size="small"
                  onClick={() => navigate('/auth/register')}
                  sx={{ ml: 0.5 }}
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

import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Box, Button, Chip, CircularProgress, Paper, Stack, Switch, Tab, Tabs, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { useAuth } from '../../store/AuthContext';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';
type UserRow = { id: number; username: string; email: string; is_active: boolean; is_developer: boolean; is_admin: boolean };
type AgentRow = { id: number; name: string; category: string; developer_id: number; is_active: boolean };

export const AdminDashboard: React.FC = () => {
  const { token, logout, user } = useAuth();
  const [tab, setTab] = useState(0);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    setBusy(true); setError('');
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [u, a] = await Promise.all([axios.get(`${API}/admin/users`, { headers }), axios.get(`${API}/admin/agents`, { headers })]);
      setUsers(u.data); setAgents(a.data);
    } catch (e: any) { setError(e.response?.data?.detail || 'Could not load admin data. Check that the API is running.'); }
    finally { setBusy(false); }
  }, [token]);
  useEffect(() => { void load(); }, [load]);
  const updateUser = async (id: number, values: Partial<UserRow>) => {
    const headers = { Authorization: `Bearer ${token}` };
    try { await axios.patch(`${API}/admin/users/${id}`, values, { headers }); await load(); }
    catch (e: any) { setError(e.response?.data?.detail || 'Could not update user.'); }
  };
  const updateAgent = async (id: number, is_active: boolean) => {
    const headers = { Authorization: `Bearer ${token}` };
    try { await axios.patch(`${API}/admin/agents/${id}`, { is_active }, { headers }); await load(); }
    catch (e: any) { setError(e.response?.data?.detail || 'Could not update listing.'); }
  };
  return <Box sx={{ maxWidth: 1200, mx: 'auto', p: { xs: 2, md: 4 } }}>
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
      <Box><Typography variant="overline" color="primary">AGENTSLEDGE CONTROL</Typography><Typography variant="h4" fontWeight={700}>Marketplace admin</Typography><Typography color="text.secondary">Signed in as {user?.username}</Typography></Box>
      <Button variant="outlined" onClick={logout}>Sign out</Button>
    </Stack>
    <Stack direction="row" spacing={2} sx={{ mb: 3 }}><Paper sx={{ p: 2, flex: 1 }}><Typography color="text.secondary">Members</Typography><Typography variant="h4">{users.length}</Typography></Paper><Paper sx={{ p: 2, flex: 1 }}><Typography color="text.secondary">Service listings</Typography><Typography variant="h4">{agents.length}</Typography></Paper><Paper sx={{ p: 2, flex: 1 }}><Typography color="text.secondary">Active listings</Typography><Typography variant="h4">{agents.filter(a => a.is_active).length}</Typography></Paper></Stack>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    <Paper><Tabs value={tab} onChange={(_, value) => setTab(value)}><Tab label={`Users (${users.length})`} /><Tab label={`Listings (${agents.length})`} /></Tabs>
      {busy ? <Box sx={{ p: 6, textAlign: 'center' }}><CircularProgress /></Box> : tab === 0 ? <Table><TableHead><TableRow><TableCell>Member</TableCell><TableCell>Email</TableCell><TableCell>Role</TableCell><TableCell>Status</TableCell><TableCell align="right">Active</TableCell></TableRow></TableHead><TableBody>{users.map(u => <TableRow key={u.id}><TableCell>{u.username}</TableCell><TableCell>{u.email}</TableCell><TableCell><Stack direction="row" spacing={1}>{u.is_admin && <Chip size="small" label="Admin" color="secondary" />}{u.is_developer && <Chip size="small" label="Developer" />}</Stack></TableCell><TableCell>{u.is_active ? 'Active' : 'Suspended'}</TableCell><TableCell align="right"><Switch checked={u.is_active} disabled={u.id === user?.id} onChange={(_, checked) => void updateUser(u.id, { is_active: checked })} inputProps={{ 'aria-label': `Set ${u.username} active` }} /></TableCell></TableRow>)}</TableBody></Table> : <Table><TableHead><TableRow><TableCell>Service</TableCell><TableCell>Category</TableCell><TableCell>Developer ID</TableCell><TableCell>Status</TableCell><TableCell align="right">Listed</TableCell></TableRow></TableHead><TableBody>{agents.map(a => <TableRow key={a.id}><TableCell>{a.name}</TableCell><TableCell>{a.category || 'Uncategorized'}</TableCell><TableCell>{a.developer_id}</TableCell><TableCell>{a.is_active ? 'Published' : 'Hidden'}</TableCell><TableCell align="right"><Switch checked={a.is_active} onChange={(_, checked) => void updateAgent(a.id, checked)} inputProps={{ 'aria-label': `Set ${a.name} published` }} /></TableCell></TableRow>)}</TableBody></Table>}</Paper>
  </Box>;
};

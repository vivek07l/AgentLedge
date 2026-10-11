import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, Switch, Tab, Tabs, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { useAuth } from '../../store/AuthContext';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';
type UserRow = { id: number; username: string; email: string; is_active: boolean; is_developer: boolean; is_admin: boolean };
type AgentRow = { id: number; name: string; description: string; category: string; capabilities: string; price: number; minimum_price: number | null; developer_id: number; is_active: boolean; implementation_key: string | null; execution_instructions: string | null; expected_input: string | null; input_schema_json: string | null; output_format: string | null; execution_available: boolean; gemini_execution_enabled: boolean };
type ListingForm = { name: string; description: string; category: string; capabilities: string; price: string; minimum_price: string; execution_instructions: string; expected_input: string; input_schema_json: string; output_format: string };
const emptyForm: ListingForm = { name: '', description: '', category: 'General', capabilities: '', price: '0', minimum_price: '', execution_instructions: '', expected_input: '', input_schema_json: '', output_format: '' };

function suggestedInstructions(agent: AgentRow) {
  return `Perform the ${agent.name} service described below. Use only the user's supplied material. Be accurate, state uncertainty, and do not claim external actions or facts that were not verified.\n\nListing description: ${agent.description}\nCategory: ${agent.category}\nCapabilities: ${agent.capabilities}`;
}

export const AdminDashboard: React.FC = () => {
  const { token, logout, user } = useAuth();
  const [tab, setTab] = useState(0);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<AgentRow | null>(null);
  const [form, setForm] = useState<ListingForm>(emptyForm);
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);
  const load = useCallback(async () => {
    setBusy(true); setError('');
    try {
      const [u, a] = await Promise.all([axios.get(`${API}/admin/users`, { headers }), axios.get(`${API}/admin/agents`, { headers })]);
      setUsers(u.data); setAgents(a.data);
    } catch (e: any) { setError(e.response?.data?.detail || 'Could not load admin data. Check that the API is running.'); }
    finally { setBusy(false); }
  }, [headers]);
  useEffect(() => { void load(); }, [load]);
  const updateUser = async (id: number, values: Partial<UserRow>) => {
    try { await axios.patch(`${API}/admin/users/${id}`, values, { headers }); await load(); }
    catch (e: any) { setError(e.response?.data?.detail || 'Could not update user.'); }
  };
  const openCreate = () => { setEditing(null); setForm(emptyForm); setError(''); setFormOpen(true); };
  const openEdit = (agent: AgentRow) => {
    setEditing(agent); setError('');
    setForm({ name: agent.name, description: agent.description, category: agent.category || 'General', capabilities: agent.capabilities || '', price: String(agent.price ?? 0), minimum_price: agent.minimum_price == null ? '' : String(agent.minimum_price), execution_instructions: agent.execution_instructions || suggestedInstructions(agent), expected_input: agent.expected_input || `Provide the text or data needed for ${agent.name}.`, input_schema_json: agent.input_schema_json || '', output_format: agent.output_format || 'Return a clear, structured response with headings where useful.' });
    setFormOpen(true);
  };
  const setField = (key: keyof ListingForm) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm(current => ({ ...current, [key]: event.target.value }));
  const saveForm = async () => {
    setSaving(true); setError(''); setNotice('');
    try {
      const base = { name: form.name.trim(), description: form.description.trim(), category: form.category.trim(), capabilities: form.capabilities.trim(), price: Number(form.price), minimum_price: form.minimum_price ? Number(form.minimum_price) : null };
      if (editing) {
        await axios.patch(`${API}/admin/agents/${editing.id}`, { ...base, implementation_key: editing.implementation_key ? 'gemini_marketplace_service' : null, execution_instructions: form.execution_instructions, expected_input: form.expected_input, input_schema_json: form.input_schema_json || null, output_format: form.output_format }, { headers });
        setNotice(editing.implementation_key ? 'Listing and Gemini instructions saved for this service.' : 'Listing and execution configuration saved. Gemini remains off until you switch it on.');
      } else {
        await axios.post(`${API}/admin/agents`, base, { headers });
        setNotice('Listing created in discovery-only mode. Configure Gemini by editing this listing.');
      }
      setFormOpen(false); await load();
    } catch (e: any) { setError(e.response?.data?.detail || 'Could not save listing. Check the fields and try again.'); }
    finally { setSaving(false); }
  };
  const toggleGemini = async (agent: AgentRow, enabled: boolean) => {
    setError(''); setNotice('');
    const instructions = agent.execution_instructions || suggestedInstructions(agent);
    const values = enabled ? {
      implementation_key: 'gemini_marketplace_service',
      execution_instructions: instructions,
      expected_input: agent.expected_input || `Provide the text or data needed for ${agent.name}.`,
      output_format: agent.output_format || 'Return a clear, structured response with headings where useful.',
    } : { implementation_key: null };
    try {
      await axios.patch(`${API}/admin/agents/${agent.id}`, values, { headers });
      await load();
      setNotice(enabled ? 'Gemini configured for this listing. It is available only if live Gemini is configured and the listing configuration is valid.' : 'Gemini execution disabled. The listing remains discoverable.');
    } catch (e: any) { setError(e.response?.data?.detail || 'Could not change Gemini execution. Edit and validate the service configuration first.'); }
  };
  const togglePublished = async (agent: AgentRow, enabled: boolean) => {
    try { await axios.patch(`${API}/admin/agents/${agent.id}`, { is_active: enabled }, { headers }); await load(); }
    catch (e: any) { setError(e.response?.data?.detail || 'Could not update listing visibility.'); }
  };
  return <Box sx={{ maxWidth: 1250, mx: 'auto', p: { xs: 2, md: 4 } }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'center' }} sx={{ mb: 3 }} gap={2}>
      <Box><Typography variant="overline" color="primary">AGENTSLEDGE CONTROL</Typography><Typography variant="h4" fontWeight={700}>Marketplace admin</Typography><Typography color="text.secondary">Signed in as {user?.username}</Typography></Box>
      <Button variant="outlined" onClick={logout}>Sign out</Button>
    </Stack>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 3 }}><Paper sx={{ p: 2, flex: 1 }}><Typography color="text.secondary">Members</Typography><Typography variant="h4">{users.length}</Typography></Paper><Paper sx={{ p: 2, flex: 1 }}><Typography color="text.secondary">Service listings</Typography><Typography variant="h4">{agents.length}</Typography></Paper><Paper sx={{ p: 2, flex: 1 }}><Typography color="text.secondary">Gemini executable</Typography><Typography variant="h4">{agents.filter(a => a.execution_available).length}</Typography></Paper></Stack>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}{notice && <Alert severity="success" sx={{ mb: 2 }}>{notice}</Alert>}
    <Paper><Tabs value={tab} onChange={(_, value) => setTab(value)}><Tab label={`Users (${users.length})`} /><Tab label={`Listings (${agents.length})`} /></Tabs>
      {busy ? <Box sx={{ p: 6, textAlign: 'center' }}><CircularProgress /></Box> : tab === 0 ? <Table><TableHead><TableRow><TableCell>Member</TableCell><TableCell>Email</TableCell><TableCell>Role</TableCell><TableCell>Status</TableCell><TableCell align="right">Provider access</TableCell><TableCell align="right">Active</TableCell></TableRow></TableHead><TableBody>{users.map(u => <TableRow key={u.id}><TableCell>{u.username}</TableCell><TableCell>{u.email}</TableCell><TableCell><Stack direction="row" spacing={1}>{u.is_admin && <Chip size="small" label="Admin" color="secondary" />}{u.is_developer && <Chip size="small" label="Provider" />}</Stack></TableCell><TableCell>{u.is_active ? 'Active' : 'Suspended'}</TableCell><TableCell align="right"><Switch checked={u.is_developer} disabled={u.is_admin} onChange={(_, checked) => void updateUser(u.id, { is_developer: checked })} inputProps={{ 'aria-label': `Set ${u.username} provider access` }} /></TableCell><TableCell align="right"><Switch checked={u.is_active} disabled={u.id === user?.id} onChange={(_, checked) => void updateUser(u.id, { is_active: checked })} inputProps={{ 'aria-label': `Set ${u.username} active` }} /></TableCell></TableRow>)}</TableBody></Table> : <>
        <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} justifyContent="space-between" sx={{ p: 2 }} gap={1}><Typography color="text.secondary">Listings in every category can be configured individually.</Typography><Button variant="contained" onClick={openCreate}>Create listing</Button></Stack>
        <Table><TableHead><TableRow><TableCell>Service</TableCell><TableCell>Category</TableCell><TableCell>Gemini execution</TableCell><TableCell>Provider</TableCell><TableCell>Status</TableCell><TableCell align="right">Manage</TableCell></TableRow></TableHead><TableBody>{agents.map(a => <TableRow key={a.id}><TableCell><Typography fontWeight={600}>{a.name}</Typography><Typography variant="caption" color="text.secondary">{a.description}</Typography></TableCell><TableCell>{a.category || 'Uncategorized'}</TableCell><TableCell><Stack direction="row" spacing={1} alignItems="center"><Switch checked={a.gemini_execution_enabled} onChange={(_, checked) => void toggleGemini(a, checked)} inputProps={{ 'aria-label': `Enable Gemini for ${a.name}` }} />{a.implementation_key && !a.gemini_execution_enabled && <Button size="small" onClick={() => void toggleGemini(a, false)}>Disable</Button>}<Chip size="small" color={a.gemini_execution_enabled ? 'success' : 'default'} label={a.gemini_execution_enabled ? 'On' : a.implementation_key ? 'Configured, unavailable' : 'Off'} /></Stack></TableCell><TableCell>{a.developer_id}</TableCell><TableCell><Switch checked={a.is_active} onChange={(_, checked) => void togglePublished(a, checked)} inputProps={{ 'aria-label': `Set ${a.name} published` }} />{a.is_active ? 'Published' : 'Hidden'}</TableCell><TableCell align="right"><Button size="small" onClick={() => openEdit(a)}>Edit configuration</Button></TableCell></TableRow>)}</TableBody></Table>
      </>}
    </Paper>
    <Dialog open={formOpen} onClose={() => !saving && setFormOpen(false)} fullWidth maxWidth="md"><DialogTitle>{editing ? `Edit ${editing.name}` : 'Create marketplace listing'}</DialogTitle><DialogContent dividers>
      <Stack spacing={2} sx={{ pt: 1 }}><Typography variant="subtitle1" fontWeight={700}>Listing details</Typography><TextField label="Service name" value={form.name} onChange={setField('name')} required /><TextField label="Description" value={form.description} onChange={setField('description')} multiline minRows={2} required /><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField label="Category" value={form.category} onChange={setField('category')} fullWidth /><TextField label="Capabilities" value={form.capabilities} onChange={setField('capabilities')} fullWidth /></Stack><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField label="Listed price (tokens)" type="number" value={form.price} onChange={setField('price')} fullWidth inputProps={{ min: 0 }} /><TextField label="Minimum negotiated price" type="number" value={form.minimum_price} onChange={setField('minimum_price')} fullWidth inputProps={{ min: 0 }} /></Stack>
      {editing ? <><Typography variant="subtitle1" fontWeight={700} sx={{ pt: 2 }}>Execution configuration</Typography><Alert severity="info">Gemini is configured per listing. New listings start discovery-only. Save service instructions here, then use the listing toggle to enable Gemini execution.</Alert><TextField label="Execution provider" value={editing.gemini_execution_enabled ? 'Gemini (live)' : 'Disabled (discovery only)'} disabled /><TextField label="Service instructions" value={form.execution_instructions} onChange={setField('execution_instructions')} multiline minRows={4} helperText="Describe the task this service should perform. Instructions are sent to Gemini with each request." /><TextField label="Expected user input" value={form.expected_input} onChange={setField('expected_input')} multiline minRows={2} /><TextField label="Optional input JSON schema" value={form.input_schema_json} onChange={setField('input_schema_json')} multiline minRows={3} helperText="Optional JSON object. Use a required array to enforce required input fields." /><TextField label="Expected output format" value={form.output_format} onChange={setField('output_format')} multiline minRows={2} /></> : <Alert severity="info">This listing will be created with Gemini disabled. Edit it afterward to configure and enable execution.</Alert>}
      </Stack></DialogContent><DialogActions><Button onClick={() => setFormOpen(false)} disabled={saving}>Cancel</Button><Button variant="contained" onClick={() => void saveForm()} disabled={saving || !form.name.trim() || !form.description.trim()}>{saving ? 'Saving…' : 'Save listing'}</Button></DialogActions></Dialog>
  </Box>;
};

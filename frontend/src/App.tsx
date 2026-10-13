import React, { useEffect, useState } from 'react';
import { getMe, login, logout, register, User } from './api/auth';
import {
  createProject,
  deleteProject,
  listProjects,
  Project,
  ProjectMember,
  APIKeyResponse,
  APIKeyCreated,
  listMembers,
  addMember,
  updateMemberRole,
  removeMember,
  listApiKeys,
  createApiKey,
  revokeApiKey
} from './api/projects';
import { getStoredToken } from './api/client';

interface HealthStatus {
  status: string;
  environment: string;
  version: string;
  phase: string;
}

const AVAILABLE_SCOPES = [
  'repo:read',
  'repo:write',
  'deploy:staging',
  'deploy:production',
  'secrets:read',
  'admin:all'
];

const ROLES = ['OWNER', 'MAINTAINER', 'DEVELOPER', 'VIEWER'];

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);

  // Auth State
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(false);

  // Projects State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState('');
  const [projectSlug, setProjectSlug] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [projectLoading, setProjectLoading] = useState<boolean>(false);
  const [projectMessage, setProjectMessage] = useState<string | null>(null);

  // Project Management Sub-views
  const [activeTab, setActiveTab] = useState<'members' | 'api-keys'>('members');

  // Members Management State
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState('DEVELOPER');
  const [memberLoading, setMemberLoading] = useState<boolean>(false);
  const [memberMessage, setMemberMessage] = useState<{ text: string; error?: boolean } | null>(null);

  // API Keys Management State
  const [apiKeys, setApiKeys] = useState<APIKeyResponse[]>([]);
  const [keyName, setKeyName] = useState('');
  const [keyExpiresDays, setKeyExpiresDays] = useState<number>(30);
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['repo:read']);
  const [createdKeyData, setCreatedKeyData] = useState<APIKeyCreated | null>(null);
  const [apiKeyLoading, setApiKeyLoading] = useState<boolean>(false);
  const [apiKeyMessage, setApiKeyMessage] = useState<{ text: string; error?: boolean } | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // 1. Check Backend Health
  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then((data: HealthStatus) => {
        setHealth(data);
        setLoadingHealth(false);
      })
      .catch(() => {
        setHealth({
          status: 'standby',
          environment: 'development',
          version: '0.1.0',
          phase: 'Phase 1 - RBAC & API Keys'
        });
        setLoadingHealth(false);
      });
  }, []);

  // 2. Fetch current user if token stored
  const loadUser = async () => {
    const token = getStoredToken();
    if (token) {
      try {
        const user = await getMe();
        setCurrentUser(user);
        loadProjects();
      } catch {
        setCurrentUser(null);
      }
    } else {
      setCurrentUser(null);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await listProjects();
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    } catch (err: any) {
      setProjectMessage(`Failed to load projects: ${err.message}`);
    }
  };

  const loadProjectDetails = async (projectId: string) => {
    try {
      const [membersData, keysData] = await Promise.all([
        listMembers(projectId),
        listApiKeys(projectId)
      ]);
      setMembers(membersData);
      setApiKeys(keysData);
    } catch (err: any) {
      console.error('Failed to load project details', err);
    }
  };

  useEffect(() => {
    if (selectedProjectId) {
      loadProjectDetails(selectedProjectId);
      setMemberMessage(null);
      setApiKeyMessage(null);
      setCreatedKeyData(null);
    }
  }, [selectedProjectId]);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      if (authMode === 'login') {
        const res = await login({ email, password });
        setCurrentUser(res.user);
      } else {
        const res = await register({ email, password, display_name: displayName });
        setCurrentUser(res.user);
      }
      setEmail('');
      setPassword('');
      setDisplayName('');
      await loadProjects();
    } catch (err: any) {
      setAuthError(err.message || 'Authentication error');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setCurrentUser(null);
    setProjects([]);
    setSelectedProjectId(null);
    setMembers([]);
    setApiKeys([]);
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setProjectMessage(null);
    setProjectLoading(true);
    try {
      const newProj = await createProject({
        name: projectName,
        slug: projectSlug,
        description: projectDesc
      });
      setProjectName('');
      setProjectSlug('');
      setProjectDesc('');
      setProjectMessage('Project successfully created!');
      await loadProjects();
      setSelectedProjectId(newProj.id);
    } catch (err: any) {
      setProjectMessage(`Error: ${err.message}`);
    } finally {
      setProjectLoading(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!window.confirm('Archive/delete this project?')) return;
    try {
      await deleteProject(projectId);
      if (selectedProjectId === projectId) {
        setSelectedProjectId(null);
      }
      await loadProjects();
    } catch (err: any) {
      setProjectMessage(`Delete failed: ${err.message}`);
    }
  };

  // Member Management Handlers
  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    setMemberMessage(null);
    setMemberLoading(true);
    try {
      await addMember(selectedProjectId, {
        email: newMemberEmail,
        role: newMemberRole
      });
      setNewMemberEmail('');
      setMemberMessage({ text: 'Member successfully added!' });
      const updated = await listMembers(selectedProjectId);
      setMembers(updated);
    } catch (err: any) {
      setMemberMessage({ text: err.message || 'Failed to add member', error: true });
    } finally {
      setMemberLoading(false);
    }
  };

  const handleUpdateRole = async (userId: string, newRole: string) => {
    if (!selectedProjectId) return;
    setMemberMessage(null);
    try {
      await updateMemberRole(selectedProjectId, userId, { role: newRole });
      setMemberMessage({ text: 'Role successfully updated' });
      const updated = await listMembers(selectedProjectId);
      setMembers(updated);
    } catch (err: any) {
      setMemberMessage({ text: err.message || 'Failed to update role', error: true });
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedProjectId) return;
    if (!window.confirm('Remove this member from the project?')) return;
    setMemberMessage(null);
    try {
      await removeMember(selectedProjectId, userId);
      setMemberMessage({ text: 'Member removed successfully' });
      const updated = await listMembers(selectedProjectId);
      setMembers(updated);
    } catch (err: any) {
      setMemberMessage({ text: err.message || 'Failed to remove member', error: true });
    }
  };

  // API Key Management Handlers
  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    setApiKeyMessage(null);
    setApiKeyLoading(true);
    try {
      const created = await createApiKey(selectedProjectId, {
        name: keyName,
        expires_in_days: keyExpiresDays > 0 ? keyExpiresDays : null,
        scopes: selectedScopes
      });
      setCreatedKeyData(created);
      setKeyName('');
      setApiKeyMessage({ text: 'API Key generated successfully!' });
      const updatedKeys = await listApiKeys(selectedProjectId);
      setApiKeys(updatedKeys);
    } catch (err: any) {
      setApiKeyMessage({ text: err.message || 'Failed to create API key', error: true });
    } finally {
      setApiKeyLoading(false);
    }
  };

  const handleRevokeApiKey = async (keyId: string) => {
    if (!selectedProjectId) return;
    if (!window.confirm('Revoke this API Key? Any automated services using this key will be denied access immediately.')) return;
    setApiKeyMessage(null);
    try {
      await revokeApiKey(selectedProjectId, keyId);
      setApiKeyMessage({ text: 'API Key revoked' });
      const updatedKeys = await listApiKeys(selectedProjectId);
      setApiKeys(updatedKeys);
    } catch (err: any) {
      setApiKeyMessage({ text: err.message || 'Failed to revoke API key', error: true });
    }
  };

  const toggleScope = (scope: string) => {
    if (selectedScopes.includes(scope)) {
      setSelectedScopes(selectedScopes.filter((s) => s !== scope));
    } else {
      setSelectedScopes([...selectedScopes, scope]);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <div style={{ maxWidth: '1080px', margin: '40px auto', padding: '24px', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '16px', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>AI DevOps Assistant</h1>
        <p style={{ margin: '8px 0 0 0', color: '#94a3b8' }}>
          Autonomous Developer Control Plane &amp; Deployment Orchestrator — Phase 1: Team RBAC &amp; API Key Lifecycle
        </p>
      </header>

      {/* Architecture Status Panel */}
      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, color: '#f1f5f9' }}>Architecture Foundation &amp; Pipeline Status</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Current Phase</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#38bdf8' }}>
              Phase 1 — RBAC &amp; API Keys
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Backend Service</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: health?.status === 'ok' ? '#4ade80' : '#f59e0b' }}>
              {loadingHealth ? 'Checking...' : health?.status?.toUpperCase()}
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Auth Methods</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#a78bfa' }}>
              Session Token + API Key
            </div>
          </div>
        </div>
      </section>

      {/* Main Authentication & Project Section */}
      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
        {!currentUser ? (
          <div style={{ background: '#0f172a', padding: '20px', borderRadius: '6px' }}>
            <div style={{ marginBottom: '16px', display: 'flex', gap: '12px' }}>
              <button
                onClick={() => setAuthMode('login')}
                style={{
                  background: authMode === 'login' ? '#0284c7' : '#334155',
                  color: '#fff',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Login
              </button>
              <button
                onClick={() => setAuthMode('register')}
                style={{
                  background: authMode === 'register' ? '#0284c7' : '#334155',
                  color: '#fff',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Register
              </button>
            </div>

            {authError && (
              <div style={{ background: '#ef444422', border: '1px solid #ef4444', color: '#fca5a5', padding: '10px', borderRadius: '4px', marginBottom: '12px' }}>
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} style={{ display: 'grid', gap: '12px', maxWidth: '400px' }}>
              {authMode === 'register' && (
                <input
                  type="text"
                  placeholder="Display Name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                  style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#fff' }}
                />
              )}
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#fff' }}
              />
              <input
                type="password"
                placeholder="Password (min 8 characters)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#fff' }}
              />
              <button
                type="submit"
                disabled={authLoading}
                style={{ background: '#38bdf8', color: '#0f172a', fontWeight: 'bold', padding: '10px', borderRadius: '4px', border: 'none', cursor: 'pointer' }}
              >
                {authLoading ? 'Authenticating...' : authMode === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            </form>
          </div>
        ) : (
          <div>
            {/* Authenticated User Banner */}
            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ color: '#94a3b8', fontSize: '13px' }}>Logged in as</span>
                <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#f8fafc' }}>
                  {currentUser.display_name} ({currentUser.email})
                </div>
                <div style={{ color: '#64748b', fontSize: '12px' }}>User ID: {currentUser.id}</div>
              </div>
              <button
                onClick={handleLogout}
                style={{ background: '#dc2626', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}
              >
                Sign Out
              </button>
            </div>

            {/* Create Project Form */}
            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '15px', margin: '0 0 12px 0', color: '#38bdf8' }}>Create New Project</h3>
              {projectMessage && (
                <div style={{ padding: '8px 12px', background: '#0284c722', border: '1px solid #0284c7', color: '#bae6fd', borderRadius: '4px', marginBottom: '12px', fontSize: '13px' }}>
                  {projectMessage}
                </div>
              )}
              <form onSubmit={handleCreateProject} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <input
                  type="text"
                  placeholder="Project Name (e.g. Platform Core)"
                  value={projectName}
                  onChange={(e) => {
                    setProjectName(e.target.value);
                    if (!projectSlug) {
                      setProjectSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''));
                    }
                  }}
                  required
                  style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#fff' }}
                />
                <input
                  type="text"
                  placeholder="Slug (e.g. platform-core)"
                  value={projectSlug}
                  onChange={(e) => setProjectSlug(e.target.value)}
                  required
                  style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#fff' }}
                />
                <input
                  type="text"
                  placeholder="Description (optional)"
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                  style={{ gridColumn: 'span 2', padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#fff' }}
                />
                <button
                  type="submit"
                  disabled={projectLoading}
                  style={{ gridColumn: 'span 2', background: '#10b981', color: '#fff', fontWeight: 'bold', padding: '10px', borderRadius: '4px', border: 'none', cursor: 'pointer' }}
                >
                  {projectLoading ? 'Creating...' : '+ Create Project'}
                </button>
              </form>
            </div>

            {/* Accessible Projects List */}
            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '15px', margin: '0 0 12px 0', color: '#f8fafc' }}>
                Projects ({projects.length})
              </h3>
              {projects.length === 0 ? (
                <p style={{ color: '#64748b', fontSize: '14px', margin: 0 }}>No projects found. Create one above to get started.</p>
              ) : (
                <div style={{ display: 'grid', gap: '8px' }}>
                  {projects.map((p) => {
                    const isSelected = p.id === selectedProjectId;
                    return (
                      <div
                        key={p.id}
                        style={{
                          background: isSelected ? '#1e293b' : '#141e33',
                          border: isSelected ? '1px solid #38bdf8' : '1px solid #1e293b',
                          padding: '12px 16px',
                          borderRadius: '6px',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <div
                          style={{ cursor: 'pointer', flex: 1 }}
                          onClick={() => setSelectedProjectId(p.id)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: 'bold', color: isSelected ? '#38bdf8' : '#f1f5f9' }}>{p.name}</span>
                            <span style={{ background: '#334155', color: '#94a3b8', fontSize: '11px', padding: '2px 6px', borderRadius: '4px' }}>
                              {p.slug}
                            </span>
                          </div>
                          {p.description && <div style={{ color: '#94a3b8', fontSize: '13px', marginTop: '4px' }}>{p.description}</div>}
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            onClick={() => setSelectedProjectId(p.id)}
                            style={{
                              background: isSelected ? '#38bdf8' : '#334155',
                              color: isSelected ? '#0f172a' : '#fff',
                              fontWeight: isSelected ? 'bold' : 'normal',
                              border: 'none',
                              padding: '6px 12px',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontSize: '12px'
                            }}
                          >
                            {isSelected ? 'Managing' : 'Select'}
                          </button>
                          <button
                            onClick={() => handleDeleteProject(p.id)}
                            style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Selected Project Control Plane: RBAC Members & API Keys */}
            {selectedProject && (
              <div style={{ background: '#0f172a', borderRadius: '6px', padding: '20px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '12px', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '18px', color: '#38bdf8' }}>
                      Project: {selectedProject.name}
                    </h3>
                    <div style={{ color: '#64748b', fontSize: '12px', marginTop: '2px' }}>
                      ID: {selectedProject.id} | Slug: {selectedProject.slug}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => setActiveTab('members')}
                      style={{
                        background: activeTab === 'members' ? '#0284c7' : '#1e293b',
                        color: '#fff',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: activeTab === 'members' ? 'bold' : 'normal'
                      }}
                    >
                      Team Members ({members.length})
                    </button>
                    <button
                      onClick={() => setActiveTab('api-keys')}
                      style={{
                        background: activeTab === 'api-keys' ? '#0284c7' : '#1e293b',
                        color: '#fff',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: activeTab === 'api-keys' ? 'bold' : 'normal'
                      }}
                    >
                      API Keys ({apiKeys.length})
                    </button>
                  </div>
                </div>

                {/* TAB 1: TEAM MEMBERS (RBAC) */}
                {activeTab === 'members' && (
                  <div>
                    {memberMessage && (
                      <div
                        style={{
                          padding: '10px 14px',
                          background: memberMessage.error ? '#ef444422' : '#10b98122',
                          border: memberMessage.error ? '1px solid #ef4444' : '1px solid #10b981',
                          color: memberMessage.error ? '#fca5a5' : '#86efac',
                          borderRadius: '4px',
                          marginBottom: '16px',
                          fontSize: '13px'
                        }}
                      >
                        {memberMessage.text}
                      </div>
                    )}

                    {/* Add Member Form */}
                    <form
                      onSubmit={handleAddMember}
                      style={{
                        background: '#1e293b',
                        padding: '14px',
                        borderRadius: '6px',
                        marginBottom: '16px',
                        display: 'grid',
                        gridTemplateColumns: '2fr 1fr auto',
                        gap: '12px',
                        alignItems: 'center'
                      }}
                    >
                      <input
                        type="email"
                        placeholder="Collaborator user email (e.g. dev@company.com)"
                        value={newMemberEmail}
                        onChange={(e) => setNewMemberEmail(e.target.value)}
                        required
                        style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                      />
                      <select
                        value={newMemberRole}
                        onChange={(e) => setNewMemberRole(e.target.value)}
                        style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                      <button
                        type="submit"
                        disabled={memberLoading}
                        style={{ background: '#38bdf8', color: '#0f172a', fontWeight: 'bold', padding: '8px 16px', borderRadius: '4px', border: 'none', cursor: 'pointer' }}
                      >
                        {memberLoading ? 'Adding...' : '+ Add Member'}
                      </button>
                    </form>

                    {/* Members Table */}
                    <div style={{ background: '#1e293b', borderRadius: '6px', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ background: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                            <th style={{ padding: '10px 14px' }}>Member</th>
                            <th style={{ padding: '10px 14px' }}>Role</th>
                            <th style={{ padding: '10px 14px' }}>Joined</th>
                            <th style={{ padding: '10px 14px', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {members.map((m) => {
                            const isCurrentUser = m.user_id === currentUser.id;
                            return (
                              <tr key={m.id} style={{ borderBottom: '1px solid #334155' }}>
                                <td style={{ padding: '10px 14px', color: '#f8fafc' }}>
                                  <div style={{ fontWeight: '500' }}>
                                    {m.user?.display_name || m.user_id} {isCurrentUser && <span style={{ color: '#38bdf8', fontSize: '11px' }}>(You)</span>}
                                  </div>
                                  <div style={{ color: '#64748b', fontSize: '11px' }}>{m.user?.email || m.user_id}</div>
                                </td>
                                <td style={{ padding: '10px 14px' }}>
                                  <select
                                    value={m.role}
                                    onChange={(e) => handleUpdateRole(m.user_id, e.target.value)}
                                    style={{
                                      background: '#0f172a',
                                      color: m.role === 'OWNER' ? '#f59e0b' : m.role === 'MAINTAINER' ? '#38bdf8' : '#e2e8f0',
                                      fontWeight: 'bold',
                                      border: '1px solid #475569',
                                      borderRadius: '4px',
                                      padding: '4px 8px',
                                      fontSize: '12px'
                                    }}
                                  >
                                    {ROLES.map((r) => (
                                      <option key={r} value={r}>
                                        {r}
                                      </option>
                                    ))}
                                  </select>
                                </td>
                                <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                                  {new Date(m.created_at).toLocaleDateString()}
                                </td>
                                <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                                  <button
                                    onClick={() => handleRemoveMember(m.user_id)}
                                    style={{
                                      background: '#ef444422',
                                      color: '#f87171',
                                      border: '1px solid #ef4444',
                                      padding: '4px 8px',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      fontSize: '11px'
                                    }}
                                  >
                                    Remove
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* TAB 2: API KEYS */}
                {activeTab === 'api-keys' && (
                  <div>
                    {apiKeyMessage && (
                      <div
                        style={{
                          padding: '10px 14px',
                          background: apiKeyMessage.error ? '#ef444422' : '#10b98122',
                          border: apiKeyMessage.error ? '1px solid #ef4444' : '1px solid #10b981',
                          color: apiKeyMessage.error ? '#fca5a5' : '#86efac',
                          borderRadius: '4px',
                          marginBottom: '16px',
                          fontSize: '13px'
                        }}
                      >
                        {apiKeyMessage.text}
                      </div>
                    )}

                    {/* Newly Created Key Alert (One-Time Secret Display) */}
                    {createdKeyData && (
                      <div
                        style={{
                          background: '#064e3b',
                          border: '1px solid #059669',
                          borderRadius: '6px',
                          padding: '16px',
                          marginBottom: '20px'
                        }}
                      >
                        <div style={{ fontWeight: 'bold', color: '#34d399', fontSize: '15px', marginBottom: '6px' }}>
                          ⚠️ Save your API Key Now!
                        </div>
                        <div style={{ color: '#d1fae5', fontSize: '13px', marginBottom: '12px' }}>
                          This secret token will <strong>never</strong> be displayed again. Store it securely in your CI/CD pipeline or environment secrets.
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <input
                            type="text"
                            readOnly
                            value={createdKeyData.raw_key}
                            style={{
                              flex: 1,
                              background: '#022c22',
                              border: '1px solid #059669',
                              color: '#6ee7b7',
                              fontFamily: 'monospace',
                              padding: '8px 12px',
                              borderRadius: '4px',
                              fontSize: '13px'
                            }}
                          />
                          <button
                            onClick={() => copyToClipboard(createdKeyData.raw_key)}
                            style={{
                              background: copiedKey ? '#10b981' : '#059669',
                              color: '#fff',
                              border: 'none',
                              padding: '8px 16px',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontWeight: 'bold'
                            }}
                          >
                            {copiedKey ? '✓ Copied!' : 'Copy Key'}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Create API Key Form */}
                    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#f8fafc' }}>Generate New API Key</h4>
                      <form onSubmit={handleCreateApiKey} style={{ display: 'grid', gap: '12px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                          <input
                            type="text"
                            placeholder="Key Name (e.g. GitHub Action Deployer)"
                            value={keyName}
                            onChange={(e) => setKeyName(e.target.value)}
                            required
                            style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                          />
                          <input
                            type="number"
                            placeholder="Expires in days (e.g. 30, 0 for never)"
                            value={keyExpiresDays}
                            onChange={(e) => setKeyExpiresDays(parseInt(e.target.value) || 0)}
                            style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                          />
                        </div>

                        {/* Scopes Selection */}
                        <div>
                          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Select Permissions / Scopes:</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                            {AVAILABLE_SCOPES.map((scope) => {
                              const active = selectedScopes.includes(scope);
                              return (
                                <button
                                  type="button"
                                  key={scope}
                                  onClick={() => toggleScope(scope)}
                                  style={{
                                    background: active ? '#0284c7' : '#0f172a',
                                    border: active ? '1px solid #38bdf8' : '1px solid #475569',
                                    color: active ? '#fff' : '#94a3b8',
                                    padding: '4px 10px',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  {active ? '✓ ' : '+ '}
                                  {scope}
                                </button>
                              );
                            })}
                          </div>
                        </div>

                        <button
                          type="submit"
                          disabled={apiKeyLoading}
                          style={{
                            background: '#10b981',
                            color: '#fff',
                            fontWeight: 'bold',
                            padding: '10px',
                            borderRadius: '4px',
                            border: 'none',
                            cursor: 'pointer',
                            marginTop: '4px'
                          }}
                        >
                          {apiKeyLoading ? 'Generating Key...' : 'Generate API Key'}
                        </button>
                      </form>
                    </div>

                    {/* Active API Keys List */}
                    <div style={{ background: '#1e293b', borderRadius: '6px', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ background: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                            <th style={{ padding: '10px 14px' }}>Name / Prefix</th>
                            <th style={{ padding: '10px 14px' }}>Scopes</th>
                            <th style={{ padding: '10px 14px' }}>Created</th>
                            <th style={{ padding: '10px 14px' }}>Expires</th>
                            <th style={{ padding: '10px 14px', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {apiKeys.length === 0 ? (
                            <tr>
                              <td colSpan={5} style={{ padding: '16px', textAlign: 'center', color: '#64748b' }}>
                                No active API keys for this project.
                              </td>
                            </tr>
                          ) : (
                            apiKeys.map((k) => (
                              <tr key={k.id} style={{ borderBottom: '1px solid #334155' }}>
                                <td style={{ padding: '10px 14px', color: '#f8fafc' }}>
                                  <div style={{ fontWeight: '500' }}>{k.name}</div>
                                  <div style={{ fontFamily: 'monospace', color: '#38bdf8', fontSize: '12px' }}>
                                    {k.key_prefix}...
                                  </div>
                                </td>
                                <td style={{ padding: '10px 14px' }}>
                                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                    {k.scopes.map((s) => (
                                      <span
                                        key={s}
                                        style={{
                                          background: '#0f172a',
                                          color: '#a78bfa',
                                          fontSize: '11px',
                                          padding: '2px 6px',
                                          borderRadius: '4px',
                                          border: '1px solid #334155'
                                        }}
                                      >
                                        {s}
                                      </span>
                                    ))}
                                  </div>
                                </td>
                                <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                                  {new Date(k.created_at).toLocaleDateString()}
                                </td>
                                <td style={{ padding: '10px 14px', color: k.expires_at ? '#cbd5e1' : '#64748b' }}>
                                  {k.expires_at ? new Date(k.expires_at).toLocaleDateString() : 'Never'}
                                </td>
                                <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                                  <button
                                    onClick={() => handleRevokeApiKey(k.id)}
                                    style={{
                                      background: '#ef444422',
                                      color: '#f87171',
                                      border: '1px solid #ef4444',
                                      padding: '4px 8px',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      fontSize: '11px'
                                    }}
                                  >
                                    Revoke
                                  </button>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Phase 0 Canonical Contracts Reference */}
      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px' }}>
        <h3 style={{ fontSize: '16px', marginTop: 0, color: '#f1f5f9' }}>Canonical Contracts Established</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '8px' }}>
          {[
            'contracts/agent_contract.md (AgentContext, AgentRequest, AgentResult)',
            'contracts/tool_contract.md (Tool Registry, Schemas, Permissions)',
            'contracts/event_contract.md (16 Lifecycle Events, Traceability)',
            'contracts/deployment_contract.md (DeploymentProvider, 10 Canonical States)',
            'contracts/memory_contract.md (Short-Term, Conversation, Project Memory)',
            'contracts/review_contract.md (Structured AI Review & Severity Risk Gates)'
          ].map((item, idx) => (
            <li key={idx} style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '4px', fontSize: '14px', color: '#cbd5e1' }}>
              ✓ {item}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

export default App;

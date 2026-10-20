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
  GitHubConnection,
  PullRequest,
  PlatformEvent,
  AgentExecutionResponse,
  listMembers,
  addMember,
  updateMemberRole,
  removeMember,
  listApiKeys,
  createApiKey,
  revokeApiKey,
  listGitHubConnections,
  connectGitHub,
  listPullRequests,
  listPlatformEvents,
  executeAgentReview
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

  // Tabs
  const [activeTab, setActiveTab] = useState<'github' | 'pull-requests' | 'events' | 'members' | 'api-keys'>('github');

  // GitHub Connections State
  const [connections, setConnections] = useState<GitHubConnection[]>([]);
  const [repoOwner, setRepoOwner] = useState('');
  const [repoName, setRepoName] = useState('');
  const [repoToken, setRepoToken] = useState('');
  const [repoSecret, setRepoSecret] = useState('');
  const [repoLoading, setRepoLoading] = useState<boolean>(false);
  const [repoMessage, setRepoMessage] = useState<{ text: string; error?: boolean } | null>(null);

  // Pull Requests State
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [prLoading, setPrLoading] = useState<boolean>(false);
  const [agentReviewingPr, setAgentReviewingPr] = useState<number | null>(null);
  const [lastAgentResult, setLastAgentResult] = useState<AgentExecutionResponse | null>(null);

  // Platform Events State
  const [platformEvents, setPlatformEvents] = useState<PlatformEvent[]>([]);

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
          phase: 'Phase 2-4: GitHub & ReAct Agent'
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
      const [membersData, keysData, connsData, prsData, eventsData] = await Promise.all([
        listMembers(projectId),
        listApiKeys(projectId),
        listGitHubConnections(projectId),
        listPullRequests(projectId),
        listPlatformEvents(projectId)
      ]);
      setMembers(membersData);
      setApiKeys(keysData);
      setConnections(connsData);
      setPullRequests(prsData);
      setPlatformEvents(eventsData);
    } catch (err: any) {
      console.error('Failed to load project details', err);
    }
  };

  useEffect(() => {
    if (selectedProjectId) {
      loadProjectDetails(selectedProjectId);
      setMemberMessage(null);
      setApiKeyMessage(null);
      setRepoMessage(null);
      setCreatedKeyData(null);
      setLastAgentResult(null);
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
    setConnections([]);
    setPullRequests([]);
    setPlatformEvents([]);
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

  // GitHub Connection Handlers
  const handleConnectGitHub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    setRepoMessage(null);
    setRepoLoading(true);
    try {
      await connectGitHub(selectedProjectId, {
        owner: repoOwner,
        repo_name: repoName,
        token: repoToken || undefined,
        webhook_secret: repoSecret || undefined
      });
      setRepoOwner('');
      setRepoName('');
      setRepoToken('');
      setRepoSecret('');
      setRepoMessage({ text: 'GitHub repository linked successfully!' });
      const updated = await listGitHubConnections(selectedProjectId);
      setConnections(updated);
    } catch (err: any) {
      setRepoMessage({ text: err.message || 'Failed to connect repository', error: true });
    } finally {
      setRepoLoading(false);
    }
  };

  const handleRefreshPullRequests = async () => {
    if (!selectedProjectId) return;
    setPrLoading(true);
    try {
      const [prs, evs] = await Promise.all([
        listPullRequests(selectedProjectId),
        listPlatformEvents(selectedProjectId)
      ]);
      setPullRequests(prs);
      setPlatformEvents(evs);
    } catch (err: any) {
      console.error(err);
    } finally {
      setPrLoading(false);
    }
  };

  const handleTriggerReview = async (pullNumber: number) => {
    if (!selectedProjectId) return;
    setAgentReviewingPr(pullNumber);
    try {
      const result = await executeAgentReview(selectedProjectId, pullNumber);
      setLastAgentResult(result);
      await handleRefreshPullRequests();
    } catch (err: any) {
      alert(`AI Review failed: ${err.message}`);
    } finally {
      setAgentReviewingPr(null);
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
    <div style={{ maxWidth: '1120px', margin: '40px auto', padding: '24px', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '16px', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>AI DevOps Assistant</h1>
        <p style={{ margin: '8px 0 0 0', color: '#94a3b8' }}>
          Autonomous Developer Control Plane &amp; Deployment Orchestrator — Phases 0–4 Live Control Plane
        </p>
      </header>

      {/* Architecture Status Panel */}
      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, color: '#f1f5f9' }}>Architecture Foundation &amp; Pipeline Status</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Current Milestone</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#38bdf8' }}>
              Phases 0–4 Active
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Webhook Gateway</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#4ade80' }}>
              HMAC-SHA256 Active
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>ReAct Agent Engine</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#a78bfa' }}>
              DeepSeek + Tool Registry
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

            {/* Selected Project Control Plane */}
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
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => setActiveTab('github')}
                      style={{
                        background: activeTab === 'github' ? '#0284c7' : '#1e293b',
                        color: '#fff',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: activeTab === 'github' ? 'bold' : 'normal'
                      }}
                    >
                      GitHub ({connections.length})
                    </button>
                    <button
                      onClick={() => setActiveTab('pull-requests')}
                      style={{
                        background: activeTab === 'pull-requests' ? '#0284c7' : '#1e293b',
                        color: '#fff',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: activeTab === 'pull-requests' ? 'bold' : 'normal'
                      }}
                    >
                      Pull Requests ({pullRequests.length})
                    </button>
                    <button
                      onClick={() => setActiveTab('events')}
                      style={{
                        background: activeTab === 'events' ? '#0284c7' : '#1e293b',
                        color: '#fff',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: activeTab === 'events' ? 'bold' : 'normal'
                      }}
                    >
                      Live Events ({platformEvents.length})
                    </button>
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
                      Team ({members.length})
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

                {/* TAB 1: GITHUB CONNECTION & WEBHOOKS */}
                {activeTab === 'github' && (
                  <div>
                    {repoMessage && (
                      <div
                        style={{
                          padding: '10px 14px',
                          background: repoMessage.error ? '#ef444422' : '#10b98122',
                          border: repoMessage.error ? '1px solid #ef4444' : '1px solid #10b981',
                          color: repoMessage.error ? '#fca5a5' : '#86efac',
                          borderRadius: '4px',
                          marginBottom: '16px',
                          fontSize: '13px'
                        }}
                      >
                        {repoMessage.text}
                      </div>
                    )}

                    {/* Connect Form */}
                    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '6px', marginBottom: '16px' }}>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#f8fafc' }}>Connect GitHub Repository</h4>
                      <form onSubmit={handleConnectGitHub} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <input
                          type="text"
                          placeholder="GitHub Owner (e.g. octocat)"
                          value={repoOwner}
                          onChange={(e) => setRepoOwner(e.target.value)}
                          required
                          style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                        />
                        <input
                          type="text"
                          placeholder="Repository Name (e.g. hello-world)"
                          value={repoName}
                          onChange={(e) => setRepoName(e.target.value)}
                          required
                          style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                        />
                        <input
                          type="password"
                          placeholder="Personal Access Token (optional, for private repos)"
                          value={repoToken}
                          onChange={(e) => setRepoToken(e.target.value)}
                          style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                        />
                        <input
                          type="password"
                          placeholder="Webhook HMAC Secret (optional)"
                          value={repoSecret}
                          onChange={(e) => setRepoSecret(e.target.value)}
                          style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#0f172a', color: '#fff' }}
                        />
                        <button
                          type="submit"
                          disabled={repoLoading}
                          style={{ gridColumn: 'span 2', background: '#38bdf8', color: '#0f172a', fontWeight: 'bold', padding: '10px', borderRadius: '4px', border: 'none', cursor: 'pointer' }}
                        >
                          {repoLoading ? 'Linking Repository...' : '+ Link GitHub Repository'}
                        </button>
                      </form>
                    </div>

                    {/* Connected Connections Table */}
                    <div style={{ background: '#1e293b', borderRadius: '6px', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ background: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                            <th style={{ padding: '10px 14px' }}>Repository</th>
                            <th style={{ padding: '10px 14px' }}>Branch</th>
                            <th style={{ padding: '10px 14px' }}>Webhook Ingestion Endpoint</th>
                            <th style={{ padding: '10px 14px' }}>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {connections.length === 0 ? (
                            <tr>
                              <td colSpan={4} style={{ padding: '16px', textAlign: 'center', color: '#64748b' }}>
                                No repositories linked yet. Add one above to begin ingesting pull requests.
                              </td>
                            </tr>
                          ) : (
                            connections.map((c) => (
                              <tr key={c.id} style={{ borderBottom: '1px solid #334155' }}>
                                <td style={{ padding: '10px 14px', color: '#38bdf8', fontWeight: 'bold' }}>
                                  {c.owner}/{c.repo_name}
                                </td>
                                <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                                  <code style={{ background: '#0f172a', padding: '2px 6px', borderRadius: '4px' }}>{c.default_branch}</code>
                                </td>
                                <td style={{ padding: '10px 14px' }}>
                                  <code style={{ background: '#0f172a', color: '#a78bfa', padding: '4px 8px', borderRadius: '4px', fontSize: '11px' }}>
                                    /api/v1/webhooks/github/{c.id}
                                  </code>
                                </td>
                                <td style={{ padding: '10px 14px' }}>
                                  <span style={{ background: '#064e3b', color: '#34d399', fontSize: '11px', padding: '2px 8px', borderRadius: '10px' }}>
                                    Connected
                                  </span>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* TAB 2: PULL REQUESTS & AI REVIEW */}
                {activeTab === 'pull-requests' && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                      <div style={{ color: '#94a3b8', fontSize: '13px' }}>
                        Pull requests ingested via GitHub webhooks with one-click ReAct AI review
                      </div>
                      <button
                        onClick={handleRefreshPullRequests}
                        disabled={prLoading}
                        style={{ background: '#1e293b', border: '1px solid #475569', color: '#f1f5f9', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                      >
                        {prLoading ? 'Refreshing...' : '↻ Refresh Feed'}
                      </button>
                    </div>

                    {/* Agent Review Output Card */}
                    {lastAgentResult && (
                      <div style={{ background: '#1e1b4b', border: '1px solid #6366f1', borderRadius: '6px', padding: '16px', marginBottom: '16px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontWeight: 'bold', color: '#c7d2fe' }}>🤖 Autonomous Agent Review Result</span>
                          <span style={{ background: '#4338ca', color: '#e0e7ff', fontSize: '11px', padding: '2px 8px', borderRadius: '10px' }}>
                            Confidence: {(lastAgentResult.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div style={{ color: '#e2e8f0', fontSize: '13px', marginBottom: '8px' }}>
                          <strong>Goal:</strong> {lastAgentResult.goal}
                        </div>
                        <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                          Actions taken: {lastAgentResult.actions_taken?.length || 0} tool calls executed via permission-guarded ToolRegistry.
                        </div>
                      </div>
                    )}

                    <div style={{ background: '#1e293b', borderRadius: '6px', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ background: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                            <th style={{ padding: '10px 14px' }}>PR #</th>
                            <th style={{ padding: '10px 14px' }}>Title</th>
                            <th style={{ padding: '10px 14px' }}>Author</th>
                            <th style={{ padding: '10px 14px' }}>Branch</th>
                            <th style={{ padding: '10px 14px' }}>Changes</th>
                            <th style={{ padding: '10px 14px', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pullRequests.length === 0 ? (
                            <tr>
                              <td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                                No pull requests found. Once linked with GitHub, webhook events will populate this feed automatically.
                              </td>
                            </tr>
                          ) : (
                            pullRequests.map((pr) => (
                              <tr key={pr.id} style={{ borderBottom: '1px solid #334155' }}>
                                <td style={{ padding: '10px 14px', color: '#38bdf8', fontWeight: 'bold' }}>
                                  #{pr.number}
                                </td>
                                <td style={{ padding: '10px 14px', color: '#f8fafc', fontWeight: '500' }}>
                                  {pr.title}
                                </td>
                                <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                                  {pr.author}
                                </td>
                                <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                                  <code>{pr.head_branch}</code> &rarr; <code>{pr.base_branch}</code>
                                </td>
                                <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                                  <span style={{ color: '#4ade80' }}>+{pr.additions}</span> / <span style={{ color: '#f87171' }}>-{pr.deletions}</span>
                                </td>
                                <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                                  <button
                                    onClick={() => handleTriggerReview(pr.number)}
                                    disabled={agentReviewingPr === pr.number}
                                    style={{
                                      background: agentReviewingPr === pr.number ? '#6366f1' : '#4f46e5',
                                      color: '#fff',
                                      border: 'none',
                                      padding: '6px 12px',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      fontSize: '12px',
                                      fontWeight: 'bold'
                                    }}
                                  >
                                    {agentReviewingPr === pr.number ? 'Analyzing...' : '⚡ Run AI Review'}
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

                {/* TAB 3: PLATFORM EVENTS STREAM */}
                {activeTab === 'events' && (
                  <div>
                    <div style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '14px' }}>
                      Canonical append-only Event Store conforming to <code>contracts/event_contract.md</code>
                    </div>
                    <div style={{ background: '#1e293b', borderRadius: '6px', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ background: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                            <th style={{ padding: '10px 14px' }}>Event Type</th>
                            <th style={{ padding: '10px 14px' }}>Actor</th>
                            <th style={{ padding: '10px 14px' }}>Trace ID</th>
                            <th style={{ padding: '10px 14px' }}>Timestamp (UTC)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {platformEvents.length === 0 ? (
                            <tr>
                              <td colSpan={4} style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>
                                No platform events recorded yet.
                              </td>
                            </tr>
                          ) : (
                            platformEvents.map((ev) => (
                              <tr key={ev.id} style={{ borderBottom: '1px solid #334155' }}>
                                <td style={{ padding: '10px 14px' }}>
                                  <span style={{ background: '#0f172a', color: '#38bdf8', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold' }}>
                                    {ev.event_type}
                                  </span>
                                </td>
                                <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                                  {ev.actor_type} ({ev.actor_id})
                                </td>
                                <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: '#94a3b8', fontSize: '12px' }}>
                                  {ev.trace_id?.substring(0, 8)}...
                                </td>
                                <td style={{ padding: '10px 14px', color: '#64748b' }}>
                                  {new Date(ev.created_at).toLocaleString()}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* TAB 4: TEAM MEMBERS (RBAC) */}
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

                {/* TAB 5: API KEYS */}
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

import React, { useEffect, useState } from 'react';
import { getMe, login, logout, register, User } from './api/auth';
import { createProject, deleteProject, listProjects, Project } from './api/projects';
import { getStoredToken } from './api/client';

interface HealthStatus {
  status: string;
  environment: string;
  version: string;
  phase: string;
}

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
  const [projectName, setProjectName] = useState('');
  const [projectSlug, setProjectSlug] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [projectLoading, setProjectLoading] = useState<boolean>(false);
  const [projectMessage, setProjectMessage] = useState<string | null>(null);

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
          phase: 'Phase 0 - Foundation'
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
    } catch (err: any) {
      setProjectMessage(`Failed to load projects: ${err.message}`);
    }
  };

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
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setProjectMessage(null);
    setProjectLoading(true);
    try {
      await createProject({
        name: projectName,
        slug: projectSlug,
        description: projectDesc
      });
      setProjectName('');
      setProjectSlug('');
      setProjectDesc('');
      setProjectMessage('Project successfully created!');
      await loadProjects();
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
      await loadProjects();
    } catch (err: any) {
      setProjectMessage(`Delete failed: ${err.message}`);
    }
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '40px auto', padding: '24px', fontFamily: 'sans-serif' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '16px', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>AI DevOps Assistant</h1>
        <p style={{ margin: '8px 0 0 0', color: '#94a3b8' }}>
          Autonomous Developer Control Plane & Deployment Orchestrator
        </p>
      </header>

      {/* Phase 0 System Status */}
      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, color: '#f1f5f9' }}>Architecture Foundation Status</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Current Phase</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#38bdf8' }}>
              Phase 0 Foundation + Phase 1 DB
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Backend Link</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: health?.status === 'ok' ? '#4ade80' : '#f59e0b' }}>
              {loadingHealth ? 'Checking...' : health?.status?.toUpperCase()}
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Target Architecture</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#f1f5f9' }}>
              Modular Monolith
            </div>
          </div>
        </div>
      </section>

      {/* Phase 1 Database & Identity Pipeline */}
      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, color: '#f1f5f9' }}>
          Phase 1: Identity & Projects Data Pipeline
        </h2>

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
            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ color: '#94a3b8', fontSize: '13px' }}>Authenticated Developer</span>
                <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#f8fafc' }}>
                  {currentUser.display_name} ({currentUser.email})
                </div>
                <div style={{ color: '#64748b', fontSize: '12px' }}>ID: {currentUser.id}</div>
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
                  placeholder="Project Name (e.g. Acme API)"
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
                  placeholder="Slug (e.g. acme-api)"
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
            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
              <h3 style={{ fontSize: '15px', margin: '0 0 12px 0', color: '#f8fafc' }}>
                Your Projects ({projects.length})
              </h3>
              {projects.length === 0 ? (
                <p style={{ color: '#64748b', fontSize: '14px', margin: 0 }}>No projects found. Create one above to get started.</p>
              ) : (
                <div style={{ display: 'grid', gap: '8px' }}>
                  {projects.map((p) => (
                    <div
                      key={p.id}
                      style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    >
                      <div>
                        <div style={{ fontWeight: 'bold', color: '#38bdf8' }}>{p.name}</div>
                        <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                          slug: {p.slug} | id: {p.id}
                        </div>
                        {p.description && <div style={{ color: '#cbd5e1', fontSize: '13px', marginTop: '4px' }}>{p.description}</div>}
                      </div>
                      <button
                        onClick={() => handleDeleteProject(p.id)}
                        style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
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

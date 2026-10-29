import React, { useState, useEffect } from 'react';
import {
  listMembers,
  addMember,
  updateMemberRole,
  removeMember,
  listApiKeys,
  createApiKey,
  revokeApiKey,
  ProjectMember,
  APIKeyResponse,
  APIKeyCreated
} from '../../api/projects';

interface TeamAndSecuritySectionProps {
  projectId: string;
}

export const TeamAndSecuritySection: React.FC<TeamAndSecuritySectionProps> = ({ projectId }) => {
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [apiKeys, setApiKeys] = useState<APIKeyResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<'members' | 'keys'>('members');

  // New Member State
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState<'ADMIN' | 'MAINTAINER' | 'DEVELOPER' | 'VIEWER'>('DEVELOPER');
  const [memberError, setMemberError] = useState<string | null>(null);

  // New API Key State
  const [keyName, setKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<APIKeyCreated | null>(null);
  const [keyError, setKeyError] = useState<string | null>(null);

  const loadData = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [membersData, keysData] = await Promise.all([
        listMembers(projectId),
        listApiKeys(projectId)
      ]);
      setMembers(membersData);
      setApiKeys(keysData);
    } catch (err: any) {
      console.error('Failed to load team data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemberEmail.trim()) return;
    setMemberError(null);
    try {
      await addMember(projectId, { email: newMemberEmail.trim(), role: newMemberRole });
      setNewMemberEmail('');
      await loadData();
    } catch (err: any) {
      setMemberError(err.message || 'Failed to add member.');
    }
  };

  const handleRoleChange = async (memberId: string, role: string) => {
    try {
      await updateMemberRole(projectId, memberId, role);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to update member role.');
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!confirm('Are you sure you want to remove this member from the project?')) return;
    try {
      await removeMember(projectId, memberId);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to remove member.');
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;
    setKeyError(null);
    try {
      const key = await createApiKey(projectId, {
        name: keyName.trim(),
        scopes: ['repo:read', 'test:run', 'deploy:staging']
      });
      setCreatedKey(key);
      setKeyName('');
      await loadData();
    } catch (err: any) {
      setKeyError(err.message || 'Failed to create API key.');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm('Revoking this key will immediately invalidate all requests using it. Proceed?')) return;
    try {
      await revokeApiKey(projectId, keyId);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to revoke API key.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Panel */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">Phase 1: Team RBAC &amp; API Security</span>
              <span className="rounded-full bg-emerald-950 border border-emerald-800 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 font-mono">
                PostgreSQL Managed
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Role-Based Access Control (RBAC), bcrypt hashed passwords, and cryptographically secure scoped API tokens.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setActiveSubTab('members')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeSubTab === 'members'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              👥 Team Members ({members.length})
            </button>
            <button
              onClick={() => setActiveSubTab('keys')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeSubTab === 'keys'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              🔑 Scoped API Keys ({apiKeys.length})
            </button>
          </div>
        </div>

        {/* Members Sub-Tab */}
        {activeSubTab === 'members' && (
          <div className="pt-4 space-y-6">
            {/* Add Member Form */}
            <form onSubmit={handleAddMember} className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-xl bg-slate-950 border border-slate-800">
              <input
                type="email"
                placeholder="colleague@company.com"
                value={newMemberEmail}
                onChange={(e) => setNewMemberEmail(e.target.value)}
                required
                className="rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <select
                value={newMemberRole}
                onChange={(e) => setNewMemberRole(e.target.value as any)}
                className="rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
              >
                <option value="ADMIN">ADMIN (Full Access)</option>
                <option value="MAINTAINER">MAINTAINER (Deploy &amp; Gate Approvals)</option>
                <option value="DEVELOPER">DEVELOPER (Trigger Runs &amp; Reviews)</option>
                <option value="VIEWER">VIEWER (Read-Only Telemetry)</option>
              </select>
              <button
                type="submit"
                className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs py-2 px-4 transition-all shadow-md"
              >
                + Add Member
              </button>
              {memberError && (
                <div className="sm:col-span-3 text-xs text-red-400 bg-red-950/60 p-2 rounded-lg border border-red-800">
                  {memberError}
                </div>
              )}
            </form>

            {/* Members Table */}
            <div className="rounded-xl border border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="p-3">User</th>
                    <th className="p-3">Role</th>
                    <th className="p-3">Added</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900/50">
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-850">
                      <td className="p-3">
                        <div className="font-semibold text-white">{m.user.display_name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">{m.user.email}</div>
                      </td>
                      <td className="p-3">
                        <select
                          value={m.role}
                          onChange={(e) => handleRoleChange(m.id, e.target.value)}
                          className="rounded bg-slate-950 border border-slate-700 py-1 px-2 text-[11px] font-mono font-semibold text-indigo-300 focus:outline-none"
                        >
                          <option value="ADMIN">ADMIN</option>
                          <option value="MAINTAINER">MAINTAINER</option>
                          <option value="DEVELOPER">DEVELOPER</option>
                          <option value="VIEWER">VIEWER</option>
                        </select>
                      </td>
                      <td className="p-3 text-[11px] text-slate-400 font-mono">
                        {new Date(m.created_at).toLocaleDateString()}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => handleRemoveMember(m.id)}
                          className="px-2.5 py-1 rounded bg-red-950/60 text-red-400 hover:bg-red-900/80 border border-red-800 text-[11px] transition-colors"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* API Keys Sub-Tab */}
        {activeSubTab === 'keys' && (
          <div className="pt-4 space-y-6">
            {/* Created Key Banner */}
            {createdKey && (
              <div className="p-4 rounded-xl bg-emerald-950/80 border border-emerald-800 text-xs text-emerald-200 space-y-2">
                <div className="font-bold flex items-center gap-1.5 text-emerald-300">
                  <span>✓ API Key Generated! Copy it now (will not be shown again):</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded border border-emerald-700/60 font-mono text-emerald-400 font-bold select-all break-all">
                  {createdKey.raw_key}
                </div>
              </div>
            )}

            {/* Create Key Form */}
            <form onSubmit={handleCreateKey} className="flex gap-3 p-4 rounded-xl bg-slate-950 border border-slate-800">
              <input
                type="text"
                placeholder="Key Name (e.g. CI/CD GitHub Actions Deployer)"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                required
                className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs py-2 px-5 transition-all shadow-md shrink-0"
              >
                + Generate Key
              </button>
            </form>

            {/* Keys Table */}
            <div className="rounded-xl border border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="p-3">Key Name</th>
                    <th className="p-3">Key Prefix</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Created</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900/50">
                  {apiKeys.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-slate-400">
                        No active API keys created for this project yet.
                      </td>
                    </tr>
                  ) : (
                    apiKeys.map((k) => (
                      <tr key={k.id} className="hover:bg-slate-850">
                        <td className="p-3 font-semibold text-white">{k.name}</td>
                        <td className="p-3 font-mono text-indigo-400">{k.key_prefix}...</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                            k.is_active ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400'
                          }`}>
                            {k.is_active ? 'ACTIVE' : 'REVOKED'}
                          </span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400 font-mono">
                          {new Date(k.created_at).toLocaleDateString()}
                        </td>
                        <td className="p-3 text-right">
                          {k.is_active && (
                            <button
                              onClick={() => handleRevokeKey(k.id)}
                              className="px-2.5 py-1 rounded bg-red-950/60 text-red-400 hover:bg-red-900/80 border border-red-800 text-[11px] transition-colors"
                            >
                              Revoke
                            </button>
                          )}
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
    </div>
  );
};

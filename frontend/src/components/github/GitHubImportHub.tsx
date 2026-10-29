import React, { useState, useEffect } from 'react';
import {
  fetchUserGithubRepos,
  connectGitHubRepository,
  importPublicGitHubRepo,
  fetchGitHubConnections,
  fetchProjectPullRequests,
  fetchPullRequestDiff,
  GitHubUserRepo,
  GitHubConnection,
  PullRequestItem,
  PullRequestDiff,
} from '../../api/github';

interface GitHubImportHubProps {
  projectId: string;
  onSelectPRForReview?: (pr: PullRequestItem) => void;
  onAssessRisk?: (pr: PullRequestItem) => void;
  onDeployPR?: (pr: PullRequestItem) => void;
  onRunMultiAgent?: (pr: PullRequestItem) => void;
}

export const GitHubImportHub: React.FC<GitHubImportHubProps> = ({
  projectId,
  onSelectPRForReview,
  onAssessRisk,
  onDeployPR,
  onRunMultiAgent,
}) => {
  // Public URL Import State
  const [publicUrl, setPublicUrl] = useState('');
  const [importingPublic, setImportingPublic] = useState(false);

  // Private Token Browser State
  const [activeImportMode, setActiveImportMode] = useState<'public' | 'token'>('public');
  const [token, setToken] = useState<string>(localStorage.getItem('nexops_github_token') || '');
  const [userRepos, setUserRepos] = useState<GitHubUserRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoSearch, setRepoSearch] = useState('');

  // Connections and Pull Requests
  const [connections, setConnections] = useState<GitHubConnection[]>([]);
  const [pullRequests, setPullRequests] = useState<PullRequestItem[]>([]);
  const [loadingPRs, setLoadingPRs] = useState(false);

  // Diff Modal State
  const [activeDiff, setActiveDiff] = useState<PullRequestDiff | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Quick preset samples
  const PRESET_REPOS = [
    { label: 'NexOps Control Plane', url: 'https://github.com/Sansfear87/NexOps' },
    { label: 'Flask Microframework', url: 'https://github.com/pallets/flask' },
    { label: 'FastAPI High-Speed API', url: 'https://github.com/tiangolo/fastapi' },
    { label: 'React Frontend UI', url: 'https://github.com/facebook/react' },
  ];

  // Load project connections and pull requests
  const loadProjectGitHubData = async () => {
    if (!projectId) return;
    setLoadingPRs(true);
    try {
      const conns = await fetchGitHubConnections(projectId);
      setConnections(conns);
      const prs = await fetchProjectPullRequests(projectId);
      setPullRequests(prs);
    } catch (err: any) {
      console.error('Failed to load GitHub connections:', err);
    } finally {
      setLoadingPRs(false);
    }
  };

  useEffect(() => {
    loadProjectGitHubData();
  }, [projectId]);

  // Handle 1-Click Public Repo Import via URL
  const handleImportPublicRepo = async (targetUrl?: string) => {
    const urlToUse = (targetUrl || publicUrl).trim();
    if (!urlToUse) {
      setStatusMessage({ type: 'error', text: 'Please enter a GitHub repository URL or owner/repo identifier.' });
      return;
    }
    if (!projectId) {
      setStatusMessage({ type: 'error', text: 'Please select or create an active project first.' });
      return;
    }

    setImportingPublic(true);
    setStatusMessage({ type: 'info', text: `Importing public repository from ${urlToUse}... Fetching branch commits and pull requests.` });

    try {
      const conn = await importPublicGitHubRepo(projectId, urlToUse);
      setStatusMessage({
        type: 'success',
        text: `Successfully imported ${conn.owner}/${conn.repo_name}! Pull requests and commits are now active for AI reviews, risk gates, and deployments.`,
      });
      setPublicUrl('');
      await loadProjectGitHubData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: `Import failed: ${err.message || 'Check if repository is public and accessible.'}`,
      });
    } finally {
      setImportingPublic(false);
    }
  };

  // Fetch user repos from GitHub API via PAT
  const handleFetchUserRepos = async () => {
    if (!token.trim()) {
      setStatusMessage({ type: 'error', text: 'Please enter a GitHub Personal Access Token to browse repositories.' });
      return;
    }
    setLoadingRepos(true);
    setStatusMessage(null);
    try {
      localStorage.setItem('nexops_github_token', token.trim());
      const repos = await fetchUserGithubRepos(token.trim());
      setUserRepos(repos);
      if (repos.length === 0) {
        setStatusMessage({ type: 'info', text: 'No repositories found or token lacks repo scope permissions.' });
      } else {
        setStatusMessage({ type: 'success', text: `Discovered ${repos.length} accessible repositories.` });
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Error fetching GitHub repos: ${err.message || 'Check your token.'}` });
    } finally {
      setLoadingRepos(false);
    }
  };

  // 1-click Import repository from PAT browser
  const handleImportRepo = async (repo: GitHubUserRepo) => {
    if (!projectId) return;
    setStatusMessage({ type: 'info', text: `Importing ${repo.full_name} into project...` });
    try {
      await connectGitHubRepository(projectId, repo.owner, repo.name, token.trim());
      setStatusMessage({ type: 'success', text: `Successfully imported ${repo.full_name}! Pull requests synchronized.` });
      await loadProjectGitHubData();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Import failed: ${err.message}` });
    }
  };

  // View Pull Request Diff
  const handleViewDiff = async (prNumber: number) => {
    setDiffLoading(true);
    try {
      const diff = await fetchPullRequestDiff(projectId, prNumber);
      setActiveDiff(diff);
    } catch (err: any) {
      alert(`Could not load diff: ${err.message}`);
    } finally {
      setDiffLoading(false);
    }
  };

  const filteredRepos = userRepos.filter((r) =>
    r.full_name.toLowerCase().includes(repoSearch.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Importer Hub Container */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">Phase 2: GitHub Repository & Codebase Ingestion</span>
              <span className="rounded-full bg-cyan-950 border border-cyan-800 px-2.5 py-0.5 text-[10px] font-semibold text-cyan-400">
                Live REST API & Webhooks
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Import public repositories via link without tokens, or connect private repos with a Personal Access Token.
            </p>
          </div>

          {/* Mode Switcher */}
          <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800 text-xs">
            <button
              onClick={() => setActiveImportMode('public')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                activeImportMode === 'public'
                  ? 'bg-cyan-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>🔗 Public Repo Link</span>
              <span className="bg-cyan-900/60 text-cyan-200 text-[9px] px-1.5 py-0.2 rounded font-mono">No Token</span>
            </button>
            <button
              onClick={() => setActiveImportMode('token')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                activeImportMode === 'token'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>🔑 Private Token Browser</span>
            </button>
          </div>
        </div>

        {/* Status Message Banner */}
        {statusMessage && (
          <div
            className={`mt-4 rounded-xl p-3.5 text-xs flex items-center justify-between border ${
              statusMessage.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200'
                : statusMessage.type === 'error'
                ? 'bg-red-950/40 border-red-800 text-red-200'
                : 'bg-cyan-950/40 border-cyan-800 text-cyan-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm">
                {statusMessage.type === 'success' ? '✓' : statusMessage.type === 'error' ? '✕' : 'ℹ'}
              </span>
              <span>{statusMessage.text}</span>
            </div>
            <button
              onClick={() => setStatusMessage(null)}
              className="text-slate-400 hover:text-white text-xs px-1"
            >
              ✕
            </button>
          </div>
        )}

        {/* Tab 1: Public Repo URL Importer */}
        {activeImportMode === 'public' && (
          <div className="mt-5 space-y-4">
            <div className="rounded-xl bg-slate-950/80 border border-slate-800/80 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <span>GitHub Public Repository URL or Identifier</span>
                  <span className="text-[10px] lowercase text-slate-500 font-normal">
                    (e.g., https://github.com/Sansfear87/NexOps or Sansfear87/NexOps)
                  </span>
                </label>
                <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-950/50 border border-emerald-800/60 px-2 py-0.5 rounded">
                  ✓ Token Free
                </span>
              </div>

              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  placeholder="https://github.com/Sansfear87/NexOps"
                  value={publicUrl}
                  onChange={(e) => setPublicUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleImportPublicRepo();
                  }}
                  className="flex-1 rounded-xl bg-slate-900 border border-slate-700 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono"
                />
                <button
                  onClick={() => handleImportPublicRepo()}
                  disabled={importingPublic}
                  className="rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold px-6 py-2.5 text-xs transition-all shadow-lg shadow-cyan-600/30 flex items-center justify-center gap-2 shrink-0"
                >
                  {importingPublic ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Importing Codebase...</span>
                    </>
                  ) : (
                    <>
                      <span>Import Public Repo</span>
                      <span>→</span>
                    </>
                  )}
                </button>
              </div>

              {/* Instant Quick-Load Presets */}
              <div className="pt-2">
                <span className="text-[11px] font-semibold text-slate-400 mr-2">Quick Presets:</span>
                <div className="inline-flex flex-wrap gap-2 mt-1">
                  {PRESET_REPOS.map((preset) => (
                    <button
                      key={preset.url}
                      onClick={() => {
                        setPublicUrl(preset.url);
                        handleImportPublicRepo(preset.url);
                      }}
                      className="rounded-lg bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] px-2.5 py-1 border border-slate-700/80 transition-all font-mono flex items-center gap-1"
                    >
                      <span className="text-cyan-400">⚡</span>
                      <span>{preset.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Private Token Browser */}
        {activeImportMode === 'token' && (
          <div className="mt-5 space-y-4">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <input
                type="password"
                placeholder="Personal Access Token (ghp_...)"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="flex-1 rounded-xl bg-slate-950 border border-slate-700 px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-full"
              />
              <button
                onClick={handleFetchUserRepos}
                disabled={loadingRepos}
                className="rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-5 py-2 text-xs transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50 shrink-0 w-full sm:w-auto justify-center"
              >
                {loadingRepos ? 'Fetching Repos...' : 'Fetch Account Repos'}
              </button>
            </div>

            {/* Repository Browser Grid */}
            {userRepos.length > 0 && (
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Discovered Repositories ({filteredRepos.length})
                  </h3>
                  <input
                    type="text"
                    placeholder="Filter repositories..."
                    value={repoSearch}
                    onChange={(e) => setRepoSearch(e.target.value)}
                    className="rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-1 text-xs text-white placeholder-slate-500 focus:outline-none w-48"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-60 overflow-y-auto pr-1">
                  {filteredRepos.map((repo) => {
                    const isConnected = connections.some((c) => c.owner === repo.owner && c.repo_name === repo.name);
                    return (
                      <div
                        key={repo.id}
                        className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 hover:border-slate-700 transition-all flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-white truncate" title={repo.full_name}>
                              {repo.full_name}
                            </span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${repo.private ? 'bg-amber-950 text-amber-400 border border-amber-800' : 'bg-slate-800 text-slate-300'}`}>
                              {repo.private ? 'Private' : 'Public'}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                            {repo.description || 'No description provided.'}
                          </p>
                        </div>

                        <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-900">
                          <div className="flex items-center space-x-2 text-[10px] text-slate-500">
                            {repo.language && <span className="text-cyan-400 font-medium">{repo.language}</span>}
                            <span>★ {repo.stars}</span>
                          </div>

                          {isConnected ? (
                            <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-800 px-2 py-0.5 rounded">
                              Connected ✓
                            </span>
                          ) : (
                            <button
                              onClick={() => handleImportRepo(repo)}
                              className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[10px] px-2.5 py-1 transition-all shadow"
                            >
                              Import →
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Connected Repositories Pill Bar */}
        {connections.length > 0 && (
          <div className="mt-5 pt-4 border-t border-slate-800 flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Active Repositories ({connections.length}):
            </span>
            {connections.map((c) => (
              <span
                key={c.id}
                className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-950/50 border border-cyan-800/80 px-2.5 py-1 text-xs font-mono text-cyan-300"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-semibold text-white">{c.owner}/{c.repo_name}</span>
                <span className="text-[10px] text-cyan-400">({c.default_branch})</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Synchronized Pull Requests & Direct Action Hub */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>Synchronized Pull Requests & Commits</span>
              <span className="rounded-full bg-slate-800 text-slate-300 text-[10px] font-bold px-2 py-0.5">
                {pullRequests.length} Active
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Live pull request feed imported from connected GitHub repositories with diff statistics and direct 1-click lifecycle triggers.
            </p>
          </div>

          <button
            onClick={loadProjectGitHubData}
            disabled={loadingPRs}
            className="rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-1.5 text-xs font-medium border border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <span>↻</span>
            <span>{loadingPRs ? 'Refreshing...' : 'Refresh Feed'}</span>
          </button>
        </div>

        {/* PR Feed Table */}
        <div className="mt-4 overflow-x-auto">
          {pullRequests.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <div className="text-3xl">📦</div>
              <p className="text-sm font-semibold text-slate-300">No pull requests found for this project yet.</p>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Paste any public GitHub repository link above (e.g. <code className="text-cyan-400 font-mono">https://github.com/Sansfear87/NexOps</code>) to immediately import pull requests, compute diffs, and test autonomous reviews.
              </p>
            </div>
          ) : (
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">PR #</th>
                  <th className="py-3 px-4">Title & Author</th>
                  <th className="py-3 px-4">Branches</th>
                  <th className="py-3 px-4">State</th>
                  <th className="py-3 px-4">Diff Impact</th>
                  <th className="py-3 px-4 text-right">Autonomous Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {pullRequests.map((pr) => (
                  <tr key={pr.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-cyan-400 text-sm">
                      #{pr.pull_number}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-white text-xs">{pr.title}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        by <span className="text-slate-300 font-medium">@{pr.author}</span> • Commit{' '}
                        <code className="text-slate-300 font-mono text-[10px] bg-slate-800 px-1 py-0.5 rounded">
                          {pr.head_sha ? pr.head_sha.substring(0, 7) : 'main'}
                        </code>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      <span className="text-indigo-400 font-semibold">{pr.head_branch}</span>
                      <span className="text-slate-500 mx-1.5">→</span>
                      <span className="text-slate-400">{pr.base_branch}</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          pr.state === 'OPEN'
                            ? 'bg-emerald-950 border border-emerald-800 text-emerald-400'
                            : pr.state === 'MERGED'
                            ? 'bg-purple-950 border border-purple-800 text-purple-400'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {pr.state}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-2 font-mono text-[11px]">
                        <span className="text-emerald-400 font-bold">+{pr.additions}</span>
                        <span className="text-red-400 font-bold">-{pr.deletions}</span>
                        <span className="text-slate-500 text-[10px]">({pr.changed_files} files)</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                      <button
                        onClick={() => handleViewDiff(pr.pull_number)}
                        className="rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 text-[11px] font-medium border border-slate-700 transition-colors"
                      >
                        Inspect Diff
                      </button>

                      {onSelectPRForReview && (
                        <button
                          onClick={() => onSelectPRForReview(pr)}
                          className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 text-[11px] font-semibold transition-all shadow shadow-indigo-600/30"
                        >
                          🤖 AI Review
                        </button>
                      )}

                      {onAssessRisk && (
                        <button
                          onClick={() => onAssessRisk(pr)}
                          className="rounded-lg bg-amber-600 hover:bg-amber-500 text-white px-2.5 py-1 text-[11px] font-semibold transition-all shadow shadow-amber-600/30"
                        >
                          🛡️ Risk Gate
                        </button>
                      )}

                      {onDeployPR && (
                        <button
                          onClick={() => onDeployPR(pr)}
                          className="rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 text-[11px] font-semibold transition-all shadow shadow-emerald-600/30"
                        >
                          🚀 Deploy
                        </button>
                      )}

                      {onRunMultiAgent && (
                        <button
                          onClick={() => onRunMultiAgent(pr)}
                          className="rounded-lg bg-purple-600 hover:bg-purple-500 text-white px-2.5 py-1 text-[11px] font-semibold transition-all shadow shadow-purple-600/30"
                        >
                          🧠 Multi-Agent
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Unified Diff Inspector Modal */}
      {activeDiff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-4xl max-h-[85vh] rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl flex flex-col text-slate-200">
            <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/60">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-white text-base">
                  Pull Request #{activeDiff.pull_number} Diff Viewer
                </span>
                <span className="text-xs text-slate-400">
                  ({activeDiff.files_changed.length} files modified)
                </span>
              </div>
              <button
                onClick={() => setActiveDiff(null)}
                className="text-slate-400 hover:text-white text-lg px-2"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 font-mono text-xs space-y-4">
              {activeDiff.files_changed.map((f, i) => (
                <div key={i} className="rounded-lg border border-slate-800 overflow-hidden bg-slate-950">
                  <div className="bg-slate-900 px-3 py-1.5 flex items-center justify-between border-b border-slate-800">
                    <span className="font-bold text-slate-200">{f.filename}</span>
                    <div className="space-x-2 text-[10px]">
                      <span className="text-emerald-400 font-bold">+{f.additions}</span>
                      <span className="text-red-400 font-bold">-{f.deletions}</span>
                      <span className="text-slate-500 uppercase">{f.status}</span>
                    </div>
                  </div>
                  <pre className="p-3 text-[11px] text-slate-300 overflow-x-auto leading-relaxed">
                    {f.patch || 'Binary file or large diff omitted.'}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

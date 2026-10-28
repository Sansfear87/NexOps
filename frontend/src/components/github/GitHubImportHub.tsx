import React, { useState, useEffect } from 'react';
import {
  fetchUserGithubRepos,
  connectGitHubRepository,
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
}

export const GitHubImportHub: React.FC<GitHubImportHubProps> = ({
  projectId,
  onSelectPRForReview,
  onAssessRisk,
  onDeployPR,
}) => {
  const [token, setToken] = useState<string>(localStorage.getItem('nexops_github_token') || '');
  const [userRepos, setUserRepos] = useState<GitHubUserRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoSearch, setRepoSearch] = useState('');

  const [connections, setConnections] = useState<GitHubConnection[]>([]);
  const [pullRequests, setPullRequests] = useState<PullRequestItem[]>([]);
  const [loadingPRs, setLoadingPRs] = useState(false);

  const [activeDiff, setActiveDiff] = useState<PullRequestDiff | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

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

  // Fetch user repos from GitHub API
  const handleFetchUserRepos = async () => {
    if (!token.trim()) {
      setStatusMessage('Please enter a GitHub Personal Access Token to browse repositories.');
      return;
    }
    setLoadingRepos(true);
    setStatusMessage(null);
    try {
      localStorage.setItem('nexops_github_token', token.trim());
      const repos = await fetchUserGithubRepos(token.trim());
      setUserRepos(repos);
      if (repos.length === 0) {
        setStatusMessage('No repositories found or token lacks repo scope permissions.');
      }
    } catch (err: any) {
      setStatusMessage(`Error fetching GitHub repos: ${err.message || 'Check your token.'}`);
    } finally {
      setLoadingRepos(false);
    }
  };

  // 1-click Import repository
  const handleImportRepo = async (repo: GitHubUserRepo) => {
    if (!projectId) return;
    setStatusMessage(`Importing ${repo.full_name} into project...`);
    try {
      await connectGitHubRepository(projectId, repo.owner, repo.name, token.trim());
      setStatusMessage(`Successfully imported ${repo.full_name}! Pull requests synchronized.`);
      await loadProjectGitHubData();
    } catch (err: any) {
      setStatusMessage(`Import failed: ${err.message}`);
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
      {/* GitHub Authentication & Importer Section */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">Phase 2: GitHub Integration & Data Showcase</span>
              <span className="rounded-full bg-cyan-950 border border-cyan-800 px-2 py-0.5 text-[10px] font-semibold text-cyan-400">
                Live API & Webhooks
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Browse repositories from your GitHub account, import them in 1 click, and stream real-time pull requests and diffs into NexOps.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="password"
              placeholder="GitHub Token (ghp_...)"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-52"
            />
            <button
              onClick={handleFetchUserRepos}
              disabled={loadingRepos}
              className="rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50"
            >
              {loadingRepos ? (
                <span>Fetching Repos...</span>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                  </svg>
                  <span>Fetch Repos</span>
                </>
              )}
            </button>
          </div>
        </div>

        {statusMessage && (
          <div className="mt-4 rounded-lg bg-cyan-950/40 border border-cyan-800/60 p-3 text-xs text-cyan-200">
            {statusMessage}
          </div>
        )}

        {/* Repository Browser Grid */}
        {userRepos.length > 0 && (
          <div className="mt-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Available Repositories ({filteredRepos.length})
              </h3>
              <input
                type="text"
                placeholder="Filter repositories..."
                value={repoSearch}
                onChange={(e) => setRepoSearch(e.target.value)}
                className="rounded-md bg-slate-950 border border-slate-800 px-2.5 py-1 text-xs text-white placeholder-slate-500 focus:outline-none w-48"
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
                          className="rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[10px] px-2.5 py-1 transition-all shadow"
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

      {/* Connected Project Repositories & Live Pull Requests Showcase */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-white">Synchronized Pull Requests</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Live pull request feed imported from connected GitHub repositories with diff statistics.
            </p>
          </div>

          <button
            onClick={loadProjectGitHubData}
            disabled={loadingPRs}
            className="rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 text-xs font-medium border border-slate-700 transition-colors"
          >
            {loadingPRs ? 'Refreshing...' : '↻ Refresh Feed'}
          </button>
        </div>

        {/* PR Feed Table */}
        <div className="mt-4 overflow-x-auto">
          {pullRequests.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-sm text-slate-400">No pull requests found for this project.</p>
              <p className="text-xs text-slate-500 mt-1">
                Connect a GitHub repository above to ingest open PRs, or trigger a webhook.
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
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {pullRequests.map((pr) => (
                  <tr key={pr.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-cyan-400">
                      #{pr.pull_number}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-white">{pr.title}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        by <span className="text-slate-300 font-medium">@{pr.author}</span> • Commit{' '}
                        <code className="text-slate-300 font-mono text-[10px] bg-slate-800 px-1 rounded">
                          {pr.head_sha.substring(0, 7)}
                        </code>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      <span className="text-indigo-400">{pr.head_branch}</span>
                      <span className="text-slate-500 mx-1">→</span>
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
                        <span className="text-emerald-400">+{pr.additions}</span>
                        <span className="text-red-400">-{pr.deletions}</span>
                        <span className="text-slate-500 text-[10px]">({pr.changed_files} files)</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                      <button
                        onClick={() => handleViewDiff(pr.pull_number)}
                        className="rounded bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 text-[11px] font-medium border border-slate-700 transition-colors"
                      >
                        Inspect Diff
                      </button>

                      {onSelectPRForReview && (
                        <button
                          onClick={() => onSelectPRForReview(pr)}
                          className="rounded bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 text-[11px] font-semibold transition-all shadow"
                        >
                          AI Review
                        </button>
                      )}

                      {onAssessRisk && (
                        <button
                          onClick={() => onAssessRisk(pr)}
                          className="rounded bg-amber-600 hover:bg-amber-500 text-white px-2.5 py-1 text-[11px] font-semibold transition-all shadow"
                        >
                          Gate
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
                      <span className="text-emerald-400">+{f.additions}</span>
                      <span className="text-red-400">-{f.deletions}</span>
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

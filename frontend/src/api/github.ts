import { apiFetch } from './client';

export interface GitHubUserRepo {
  id: number;
  name: string;
  full_name: string;
  owner: string;
  description?: string | null;
  default_branch: string;
  stars: number;
  language?: string | null;
  private: boolean;
  updated_at?: string;
  html_url?: string;
}

export interface GitHubConnection {
  id: string;
  project_id: string;
  owner: string;
  repo_name: string;
  default_branch: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PullRequestItem {
  id: string;
  github_connection_id: string;
  pull_number: number;
  title: string;
  state: 'OPEN' | 'CLOSED' | 'MERGED';
  author: string;
  head_branch: string;
  base_branch: string;
  head_sha: string;
  body?: string | null;
  additions: number;
  deletions: number;
  changed_files: number;
  diff_text?: string | null;
  github_created_at: string;
  github_updated_at: string;
}

export interface PullRequestDiff {
  pull_number: number;
  diff_text: string;
  files_changed: Array<{
    filename: string;
    status: string;
    additions: number;
    deletions: number;
    patch?: string;
  }>;
}

export async function fetchUserGithubRepos(token?: string): Promise<GitHubUserRepo[]> {
  const storedToken = token || localStorage.getItem('nexops_github_token') || '';
  const query = storedToken ? `?token=${encodeURIComponent(storedToken)}` : '';
  return apiFetch<GitHubUserRepo[]>(`/github/user-repos${query}`);
}

export async function connectGitHubRepository(
  projectId: string,
  owner: string,
  repo: string,
  token: string
): Promise<GitHubConnection> {
  return apiFetch<GitHubConnection>(`/projects/${projectId}/github/connect`, {
    method: 'POST',
    body: JSON.stringify({
      owner,
      repo,
      token,
      default_branch: 'main',
    }),
  });
}

export async function fetchGitHubConnections(projectId: string): Promise<GitHubConnection[]> {
  return apiFetch<GitHubConnection[]>(`/projects/${projectId}/github/connections`);
}

export async function fetchProjectPullRequests(
  projectId: string,
  connectionId?: string
): Promise<PullRequestItem[]> {
  const query = connectionId ? `?connection_id=${connectionId}` : '';
  return apiFetch<PullRequestItem[]>(`/projects/${projectId}/github/pulls${query}`);
}

export async function fetchPullRequestDetail(
  projectId: string,
  pullNumber: number
): Promise<PullRequestItem> {
  return apiFetch<PullRequestItem>(`/projects/${projectId}/github/pulls/${pullNumber}`);
}

export async function fetchPullRequestDiff(
  projectId: string,
  pullNumber: number
): Promise<PullRequestDiff> {
  return apiFetch<PullRequestDiff>(`/projects/${projectId}/github/pulls/${pullNumber}/diff`);
}

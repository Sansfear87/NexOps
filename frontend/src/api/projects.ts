import { apiFetch } from './client';
import { User } from './auth';

export interface ProjectMember {
  id: string;
  user_id: string;
  role: string;
  created_at: string;
  user?: User;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  owner_id: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  owner?: User;
  members: ProjectMember[];
}

export interface CreateProjectPayload {
  name: string;
  slug: string;
  description?: string;
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  return apiFetch<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listProjects(): Promise<Project[]> {
  return apiFetch<Project[]>('/projects', {
    method: 'GET'
  });
}

export async function getProject(projectId: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${projectId}`, {
    method: 'GET'
  });
}

export async function deleteProject(projectId: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/projects/${projectId}`, {
    method: 'DELETE'
  });
}

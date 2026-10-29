import React from 'react';
import { User } from '../../api/auth';
import { Project } from '../../api/projects';

interface NavbarProps {
  currentUser: User | null;
  projects: Project[];
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onOpenCreateProject: () => void;
  onOpenAuth: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  projects,
  activeProject,
  onSelectProject,
  onOpenCreateProject,
  onOpenAuth,
  onLogout,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-md px-4 sm:px-6 py-3.5">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Brand & Project Selector */}
        <div className="flex items-center space-x-4 sm:space-x-6">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 flex items-center justify-center font-black text-white text-lg shadow-lg shadow-indigo-500/20">
              N
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-white text-base tracking-tight">NexOps</span>
                <span className="rounded-full bg-emerald-950 border border-emerald-800/80 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 uppercase tracking-wider font-mono">
                  Phases 0–14 Live
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">Autonomous AI DevOps Control Plane</p>
            </div>
          </div>

          <div className="h-6 w-px bg-slate-800 hidden md:block" />

          {/* Project Dropdown */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-medium hidden sm:inline font-mono">Project:</span>
            {projects.length > 0 ? (
              <select
                value={activeProject?.id || ''}
                onChange={(e) => {
                  const proj = projects.find((p) => p.id === e.target.value);
                  if (proj) onSelectProject(proj);
                }}
                className="rounded-lg bg-slate-900 border border-slate-700 py-1.5 px-3 text-xs text-white font-medium focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.slug})
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-amber-400 bg-amber-950/40 border border-amber-900/60 px-2.5 py-1 rounded-md">
                No active project
              </span>
            )}

            <button
              onClick={onOpenCreateProject}
              className="rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 py-1.5 px-2.5 text-xs text-slate-200 transition-colors font-medium flex items-center gap-1"
              title="Create New Project"
            >
              <span>+</span>
              <span className="hidden sm:inline">New</span>
            </button>
          </div>
        </div>

        {/* User Profile & Actions */}
        <div className="flex items-center space-x-3">
          {currentUser ? (
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 rounded-full py-1 pl-1 pr-3">
                {currentUser.avatar_url ? (
                  <img
                    src={currentUser.avatar_url}
                    alt={currentUser.display_name}
                    className="h-6 w-6 rounded-full object-cover border border-slate-700"
                  />
                ) : (
                  <div className="h-6 w-6 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-800 flex items-center justify-center text-[10px] font-bold text-white shadow">
                    {currentUser.display_name ? currentUser.display_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                )}
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-slate-200 leading-tight">
                    {currentUser.display_name}
                  </span>
                  <span className="text-[10px] text-slate-400 leading-tight font-mono">
                    {currentUser.email}
                  </span>
                </div>
              </div>

              <button
                onClick={onLogout}
                className="rounded-lg bg-slate-800/80 hover:bg-red-950 hover:text-red-300 hover:border-red-800 border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition-all flex items-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              <span>Sign In / GitHub Auth</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

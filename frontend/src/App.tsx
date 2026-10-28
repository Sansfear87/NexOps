import React, { useState, useEffect } from 'react';
import { getMe, User } from './api/auth';
import { listProjects, Project } from './api/projects';
import { Navbar } from './components/layout/Navbar';
import { AuthModal } from './components/auth/AuthModal';
import { CreateProjectModal } from './components/layout/CreateProjectModal';
import { GitHubImportHub } from './components/github/GitHubImportHub';
import { CodeReviewSection } from './components/reviews/CodeReviewSection';
import { RiskGuardrailsSection } from './components/gates/RiskGuardrailsSection';
import { DeploymentsSection } from './components/deployments/DeploymentsSection';
import { HealthMonitoringSection } from './components/monitoring/HealthMonitoringSection';
import { IncidentRecoverySection } from './components/incidents/IncidentRecoverySection';
import { SemanticMemorySection } from './components/memory/SemanticMemorySection';
import { ModelRoutingSection } from './components/models/ModelRoutingSection';
import { PullRequestItem } from './api/github';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);

  const [activeTab, setActiveTab] = useState<
    'github' | 'reviews' | 'gates' | 'deployments' | 'monitoring' | 'incidents' | 'memory' | 'models'
  >('github');

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [selectedPRNumber, setSelectedPRNumber] = useState<number>(1);

  // Initialize Auth & Projects
  useEffect(() => {
    const init = async () => {
      try {
        const user = await getMe();
        setCurrentUser(user);
      } catch {
        // Not logged in or expired
      }

      try {
        const projs = await listProjects();
        setProjects(projs);
        if (projs.length > 0) {
          setActiveProject(projs[0]);
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
      }
    };
    init();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('nexops_session_token');
    localStorage.removeItem('nexops_github_token');
    setCurrentUser(null);
  };

  const handleSelectPRForReview = (pr: PullRequestItem) => {
    setSelectedPRNumber(pr.pull_number);
    setActiveTab('reviews');
  };

  const handleAssessRisk = (pr: PullRequestItem) => {
    setSelectedPRNumber(pr.pull_number);
    setActiveTab('gates');
  };

  const handleDeployPR = (_pr: PullRequestItem) => {
    setActiveTab('deployments');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        currentUser={currentUser}
        projects={projects}
        activeProject={activeProject}
        onSelectProject={(p) => setActiveProject(p)}
        onOpenCreateProject={() => setIsCreateProjectOpen(true)}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Phase Navigation Tabs */}
        <div className="flex flex-wrap gap-1.5 p-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
          {[
            { id: 'github', label: 'Phase 2: GitHub Showcase & Import', badge: 'Data' },
            { id: 'reviews', label: 'Phase 6: Multi-Agent AI Review', badge: 'DeepSeek' },
            { id: 'gates', label: 'Phase 7: Risk & Safety Gates', badge: 'Policy' },
            { id: 'deployments', label: 'Phase 8: Multi-Cloud Deploy', badge: 'Render' },
            { id: 'monitoring', label: 'Phase 9: Health Probes', badge: 'Telemetry' },
            { id: 'incidents', label: 'Phase 10: Incident Recovery', badge: 'Self-Heal' },
            { id: 'memory', label: 'Phase 11: Semantic Memory', badge: 'pgvector' },
            { id: 'models', label: 'Phase 12: Dual-Model Router', badge: 'Nebius' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-slate-800 text-white shadow-md border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                  activeTab === tab.id
                    ? 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {tab.badge}
              </span>
            </button>
          ))}
        </div>

        {/* Active Phase Content Section */}
        {activeProject ? (
          <div>
            {activeTab === 'github' && (
              <GitHubImportHub
                projectId={activeProject.id}
                onSelectPRForReview={handleSelectPRForReview}
                onAssessRisk={handleAssessRisk}
                onDeployPR={handleDeployPR}
              />
            )}

            {activeTab === 'reviews' && (
              <CodeReviewSection
                projectId={activeProject.id}
                selectedPRNumber={selectedPRNumber}
              />
            )}

            {activeTab === 'gates' && (
              <RiskGuardrailsSection
                projectId={activeProject.id}
                selectedPRNumber={selectedPRNumber}
              />
            )}

            {activeTab === 'deployments' && (
              <DeploymentsSection projectId={activeProject.id} />
            )}

            {activeTab === 'monitoring' && (
              <HealthMonitoringSection projectId={activeProject.id} />
            )}

            {activeTab === 'incidents' && (
              <IncidentRecoverySection projectId={activeProject.id} />
            )}

            {activeTab === 'memory' && (
              <SemanticMemorySection projectId={activeProject.id} />
            )}

            {activeTab === 'models' && <ModelRoutingSection />}
          </div>
        ) : (
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-12 text-center space-y-4 shadow-xl">
            <div className="h-12 w-12 rounded-2xl bg-indigo-950 border border-indigo-800 text-indigo-400 font-bold flex items-center justify-center mx-auto text-xl">
              N
            </div>
            <h3 className="text-lg font-bold text-white">Welcome to NexOps Autonomous Control Plane</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Please sign in with your GitHub token or create your first project to unlock multi-agent code reviews, risk guardrails, and automated deployments.
            </p>
            <div className="flex justify-center gap-3 pt-2">
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 text-xs transition-all shadow"
              >
                Sign in with GitHub / Email
              </button>
              <button
                onClick={() => setIsCreateProjectOpen(true)}
                className="rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-semibold px-4 py-2 text-xs transition-all border border-slate-700"
              >
                + Create Project
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Modals */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={(user) => setCurrentUser(user)}
      />

      <CreateProjectModal
        isOpen={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        onCreated={(proj) => {
          setProjects((prev) => [...prev, proj]);
          setActiveProject(proj);
        }}
      />
    </div>
  );
};

export default App;

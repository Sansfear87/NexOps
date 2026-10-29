import React, { useState, useEffect } from 'react';
import { getMe, User } from './api/auth';
import { listProjects, Project } from './api/projects';
import { Navbar } from './components/layout/Navbar';
import { AuthModal } from './components/auth/AuthModal';
import { CreateProjectModal } from './components/layout/CreateProjectModal';
import { SystemOverviewSection } from './components/overview/SystemOverviewSection';
import { MultiAgentOrchestratorSection } from './components/orchestrator/MultiAgentOrchestratorSection';
import { GitHubImportHub } from './components/github/GitHubImportHub';
import { CodeReviewSection } from './components/reviews/CodeReviewSection';
import { RiskGuardrailsSection } from './components/gates/RiskGuardrailsSection';
import { DeploymentsSection } from './components/deployments/DeploymentsSection';
import { HealthMonitoringSection } from './components/monitoring/HealthMonitoringSection';
import { IncidentRecoverySection } from './components/incidents/IncidentRecoverySection';
import { SemanticMemorySection } from './components/memory/SemanticMemorySection';
import { ModelRoutingSection } from './components/models/ModelRoutingSection';
import { TeamAndSecuritySection } from './components/team/TeamAndSecuritySection';
import { EventAuditSection } from './components/events/EventAuditSection';
import { PullRequestItem } from './api/github';

export type ActiveTabType =
  | 'overview'
  | 'orchestrator'
  | 'github'
  | 'reviews'
  | 'gates'
  | 'deployments'
  | 'monitoring'
  | 'incidents'
  | 'memory'
  | 'models'
  | 'team'
  | 'events';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTabType>('overview');

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

  const handleRunMultiAgent = (_pr: PullRequestItem) => {
    setActiveTab('orchestrator');
  };

  const handleQuickStartProject = async () => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }
    try {
      const { createProject } = await import('./api/projects');
      const newProj = await createProject({
        name: 'NexOps Production Platform',
        slug: 'nexops-platform-' + Math.floor(Math.random() * 1000),
        description: 'Autonomous DevOps Control Plane for repository review, guardrail verification, and cloud deployments.',
      });
      setProjects((prev) => [...prev, newProj]);
      setActiveProject(newProj);
    } catch (err: any) {
      setIsAuthModalOpen(true);
    }
  };

  const navTabs: Array<{ id: ActiveTabType; label: string; badge: string; phase: string }> = [
    { id: 'overview', label: 'Overview', badge: '14 Phases', phase: 'P0–14' },
    { id: 'orchestrator', label: 'Multi-Agent', badge: '5 Personas', phase: 'P14' },
    { id: 'github', label: 'GitHub & Code', badge: 'Webhook', phase: 'P2' },
    { id: 'reviews', label: 'AI Review & Tests', badge: 'DeepSeek', phase: 'P6' },
    { id: 'gates', label: 'Risk Guardrails', badge: 'Policy', phase: 'P7' },
    { id: 'deployments', label: 'Deployments', badge: 'Render', phase: 'P8' },
    { id: 'monitoring', label: 'Telemetry & Probes', badge: 'Metrics', phase: 'P9' },
    { id: 'incidents', label: 'Incident Healing', badge: 'Self-Heal', phase: 'P10' },
    { id: 'memory', label: 'Project Memory', badge: 'pgvector', phase: 'P11' },
    { id: 'models', label: 'Token Factory', badge: 'Nebius', phase: 'P12' },
    { id: 'team', label: 'Team & RBAC', badge: 'Security', phase: 'P1' },
    { id: 'events', label: 'Audit Trail', badge: 'Events', phase: 'P2-4' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-600 selection:text-white">
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
        <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-slate-900/90 border border-slate-800 text-xs overflow-x-auto shadow-lg backdrop-blur-md">
          {navTabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl font-medium transition-all shrink-0 ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 border border-indigo-400/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 border border-transparent'
                }`}
              >
                <span className="font-semibold">{tab.label}</span>
                <span
                  className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
                    isActive
                      ? 'bg-indigo-950/80 text-indigo-200 border border-indigo-400/40'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {tab.phase}
                </span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Section */}
        {activeTab === 'overview' && (
          <SystemOverviewSection onSelectTab={(t) => setActiveTab(t as ActiveTabType)} />
        )}

        {activeTab === 'models' && <ModelRoutingSection />}

        {/* Project Scoped Sections */}
        {activeProject ? (
          <div>
            {activeTab === 'orchestrator' && (
              <MultiAgentOrchestratorSection projectId={activeProject.id} />
            )}

            {activeTab === 'github' && (
              <GitHubImportHub
                projectId={activeProject.id}
                onSelectPRForReview={handleSelectPRForReview}
                onAssessRisk={handleAssessRisk}
                onDeployPR={handleDeployPR}
                onRunMultiAgent={handleRunMultiAgent}
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

            {activeTab === 'team' && (
              <TeamAndSecuritySection projectId={activeProject.id} />
            )}

            {activeTab === 'events' && (
              <EventAuditSection projectId={activeProject.id} />
            )}
          </div>
        ) : activeTab !== 'overview' && activeTab !== 'models' ? (
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-12 text-center space-y-4 shadow-xl">
            <div className="h-12 w-12 rounded-2xl bg-indigo-950 border border-indigo-800 text-indigo-400 font-bold flex items-center justify-center mx-auto text-xl shadow">
              N
            </div>
            <h3 className="text-lg font-bold text-white">Project Required for This Phase</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Please sign in with your GitHub token or create your first project above to unlock autonomous multi-agent orchestrations, code reviews, risk guardrails, and cloud deployments.
            </p>
            <div className="flex justify-center flex-wrap gap-3 pt-2">
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 text-xs transition-all shadow-md shadow-indigo-600/30"
              >
                Sign In with GitHub / Email
              </button>
              <button
                onClick={handleQuickStartProject}
                className="rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold px-4 py-2 text-xs transition-all shadow-md shadow-cyan-600/30"
              >
                ⚡ 1-Click Launch Project
              </button>
              <button
                onClick={() => setIsCreateProjectOpen(true)}
                className="rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold px-4 py-2 text-xs transition-all border border-slate-700"
              >
                + Custom Project
              </button>
            </div>
          </div>
        ) : null}
      </main>

      {/* Modals */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={async (user) => {
          setCurrentUser(user);
          try {
            const projs = await listProjects();
            setProjects(projs);
            if (projs.length > 0) {
              setActiveProject(projs[0]);
            }
          } catch (err) {
            console.error('Failed to load user projects:', err);
          }
        }}
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

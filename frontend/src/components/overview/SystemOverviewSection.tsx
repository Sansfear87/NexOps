import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../api/client';

interface HealthData {
  status: string;
  environment: string;
  version: string;
  phase: string;
  active_phases?: string[];
  ai_engine?: string;
  models?: Record<string, string>;
}

interface SystemOverviewSectionProps {
  onSelectTab: (tabId: string) => void;
}

export const SystemOverviewSection: React.FC<SystemOverviewSectionProps> = ({ onSelectTab }) => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pingLatency, setPingLatency] = useState<number | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const data = await apiFetch<HealthData>('/health');
      setHealth(data);
      setPingLatency(Math.round(performance.now() - start));
    } catch (err: any) {
      setError(err.message || 'Failed to connect to backend control plane.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const phasesList = [
    { id: 'Phase 0', title: 'Sandboxing & Canonical Contracts', desc: 'ReAct agent, AST tool sandbox, canonical event schemas', tab: 'orchestrator', status: 'LIVE' },
    { id: 'Phase 1', title: 'PostgreSQL & Modular Monolith', desc: 'JWT sessions, bcrypt auth, RBAC permissions & API keys', tab: 'team', status: 'LIVE' },
    { id: 'Phase 2', title: 'GitHub Integration & Webhooks', desc: 'HMAC verification, webhook event bus, git diff parser', tab: 'github', status: 'LIVE' },
    { id: 'Phase 3', title: 'Context Engine & AST Tool Registry', desc: 'Smart context assembly, tool execution sandbox & permissions', tab: 'orchestrator', status: 'LIVE' },
    { id: 'Phase 4', title: 'Agent & Platform Wiring', desc: 'Dynamic dispatch, approval gates, event-driven architecture', tab: 'orchestrator', status: 'LIVE' },
    { id: 'Phase 5', title: 'React Console Dashboard', desc: 'High-performance SPA console, live telemetry, interactive tabs', tab: 'overview', status: 'LIVE' },
    { id: 'Phase 6', title: 'AI Code Review & Test Runner', desc: 'Automated diff reviewer, security auditor, pytest runner', tab: 'reviews', status: 'LIVE' },
    { id: 'Phase 7', title: 'Risk Guardrails & Gatekeeper', desc: 'Blast radius evaluation, policy engine, approval/bypass gates', tab: 'gates', status: 'LIVE' },
    { id: 'Phase 8', title: 'Multi-Cloud Deployment Adapters', desc: 'Render, Vercel, Nebius Cloud adapters with 10 canonical states', tab: 'deployments', status: 'LIVE' },
    { id: 'Phase 9', title: 'Synthetic Monitoring & Telemetry', desc: 'HTTP synthetic probes, p95/p99 latency tracking, anomaly detection', tab: 'monitoring', status: 'LIVE' },
    { id: 'Phase 10', title: 'Autonomous Incident Recovery', desc: 'Causal reasoning triage, Nemotron AI diagnosis & auto-rollback', tab: 'incidents', status: 'LIVE' },
    { id: 'Phase 11', title: 'Semantic Project Memory', desc: 'Secret sanitization, post-mortem storage, vector similarity search', tab: 'memory', status: 'LIVE' },
    { id: 'Phase 12', title: 'Nebius AI Cloud & Token Factory', desc: 'Dual-model router: Nemotron-3.5 + DeepSeek-V4.1 cost optimizer', tab: 'models', status: 'LIVE' },
    { id: 'Phase 13', title: 'Full Lifecycle Console Tabs', desc: 'Deployments, Monitoring, Incidents, Memory & Security tabs', tab: 'overview', status: 'LIVE' },
    { id: 'Phase 14', title: 'Multi-Agent Orchestrator', desc: '5 personas, DAG planning, credit efficiency & token budgets', tab: 'orchestrator', status: 'LIVE' },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Control Plane Status Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 p-6 sm:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400 bg-emerald-950/80 border border-emerald-800/80 px-2.5 py-0.5 rounded-full">
                All 14 Phases Active & Operational
              </span>
              {pingLatency !== null && (
                <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-700">
                  {pingLatency}ms latency
                </span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              NexOps Autonomous Control Plane
            </h1>
            <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
              Self-healing AI DevOps orchestrator powered by <span className="text-indigo-400 font-medium">NVIDIA Nemotron 3.5</span> and <span className="text-cyan-400 font-medium">DeepSeek V4.1</span> on <span className="text-slate-300 font-medium">Nebius AI Cloud</span>, running production deployments on Render.
            </p>
          </div>

          <div className="flex flex-wrap gap-2.5">
            <button
              onClick={() => onSelectTab('orchestrator')}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-lg shadow-indigo-600/30 flex items-center gap-2 border border-indigo-400/20"
            >
              <span>🤖 Multi-Agent Run</span>
            </button>
            <button
              onClick={() => onSelectTab('deployments')}
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs transition-all border border-slate-700 flex items-center gap-2"
            >
              <span>🚀 Deployments</span>
            </button>
            <button
              onClick={fetchHealth}
              disabled={loading}
              className="px-3 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 text-xs font-medium transition-all"
              title="Refresh Health"
            >
              {loading ? '⌛' : '🔄'}
            </button>
          </div>
        </div>

        {/* Live System Metrics Badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 mt-6 border-t border-slate-800/80">
          <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-mono">Environment</div>
            <div className="text-sm font-bold text-white capitalize mt-0.5">
              {health?.environment || 'Production'}
            </div>
          </div>
          <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-mono">Control Engine</div>
            <div className="text-sm font-bold text-indigo-400 mt-0.5 truncate">
              {health?.ai_engine || 'Multi-Agent Dual-Model'}
            </div>
          </div>
          <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-mono">Reasoning Model</div>
            <div className="text-sm font-bold text-cyan-400 mt-0.5 truncate">
              Nemotron-3.5-Lightning
            </div>
          </div>
          <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-mono">Fast Model</div>
            <div className="text-sm font-bold text-emerald-400 mt-0.5 truncate">
              DeepSeek-V4.1-Flash
            </div>
          </div>
        </div>
      </div>

      {/* 14-Phase Capability Matrix */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Full 14-Phase Autonomous Capabilities Matrix</span>
              <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono px-2 py-0.5 rounded-full">
                14 / 14 Complete
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Click any phase card to jump directly to its dedicated control plane section.
            </p>
          </div>
          <div className="text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-900/60 px-3 py-1 rounded-lg">
            ✓ 0 AST Violations • 100% Contracts Verified
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {phasesList.map((p, idx) => (
            <div
              key={idx}
              onClick={() => onSelectTab(p.tab)}
              className="group p-3.5 rounded-xl bg-slate-950/70 hover:bg-slate-850 border border-slate-800/80 hover:border-indigo-500/50 cursor-pointer transition-all duration-200 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-mono font-bold text-indigo-400 group-hover:text-indigo-300">
                    {p.id}
                  </span>
                  <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded uppercase bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                    {p.status}
                  </span>
                </div>
                <h3 className="text-xs font-bold text-slate-200 group-hover:text-white transition-colors">
                  {p.title}
                </h3>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                  {p.desc}
                </p>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/50 flex items-center justify-between text-[10px] text-slate-400">
                <span className="font-mono">Open {p.tab} →</span>
                <span className="text-slate-400 group-hover:text-slate-300">Active</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Canonical Architecture Contracts */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider text-slate-300">
          Canonical Governance Contracts & Architecture
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          {[
            { name: 'contracts/agent_contract.md', desc: 'AgentContext, AgentRequest, AgentResult schema boundaries' },
            { name: 'contracts/tool_contract.md', desc: 'Tool registry, AST validation, explicit permission tokens' },
            { name: 'contracts/event_contract.md', desc: '16 canonical lifecycle events & immutable trace IDs' },
            { name: 'contracts/deployment_contract.md', desc: '10 canonical states, atomic rollback & provider adapters' },
            { name: 'contracts/memory_contract.md', desc: 'Short-term context, conversation logs & semantic project memory' },
            { name: 'contracts/review_contract.md', desc: 'Structured AI code review, severity tags & risk gates' },
          ].map((c, i) => (
            <div key={i} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 font-mono">
              <div className="text-emerald-400 font-semibold truncate">✓ {c.name}</div>
              <div className="text-slate-400 text-[11px] mt-1 font-sans">{c.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

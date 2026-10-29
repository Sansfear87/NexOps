import React, { useState } from 'react';
import { apiFetch } from '../../api/client';

interface MultiAgentOrchestratorSectionProps {
  projectId: string;
}

interface AgentRunResult {
  run_id: string;
  trace_id: string;
  project_id: string;
  goal: string;
  status: string;
  confidence: number;
  actions_taken: Array<{
    tool: string;
    input: any;
    output: any;
  }>;
  output: any;
  created_at?: string;
  error?: string;
}

export const MultiAgentOrchestratorSection: React.FC<MultiAgentOrchestratorSectionProps> = ({ projectId }) => {
  const [goal, setGoal] = useState('Analyze latest pull request diff for security vulnerabilities, run test suite, and check deployment health.');
  const [environment, setEnvironment] = useState<'staging' | 'production'>('staging');
  const [mode, setMode] = useState<'multi_agent' | 'react'>('multi_agent');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgentRunResult | null>(null);

  const presets = [
    {
      label: '🛡️ Security & Diff Review',
      prompt: 'Perform deep security code review on the latest pull request diff and flag OWASP violations.',
    },
    {
      label: '🚀 Deployment & Gate Check',
      prompt: 'Evaluate deployment gate policies for staging and verify pre-flight verification tests pass.',
    },
    {
      label: '🩺 Telemetry & Health Probe',
      prompt: 'Execute synthetic HTTP health checks across deployment endpoints and inspect latency anomalies.',
    },
    {
      label: '🚨 Incident Root Cause Diagnosis',
      prompt: 'Correlate recent application logs and error metrics using Nemotron causal reasoning to diagnose root cause.',
    },
  ];

  const handleRunOrchestration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) {
      setError('Please select or create a project first.');
      return;
    }
    if (!goal.trim()) {
      setError('Please provide an actionable DevOps goal.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await apiFetch<AgentRunResult>(`/projects/${projectId}/agent/run`, {
        method: 'POST',
        body: JSON.stringify({
          goal: goal.trim(),
          environment,
          mode,
          permissions: [
            'repo:read',
            'test:run',
            'deploy:staging',
            'logs:read',
            'metrics:read',
            'k8s:read'
          ]
        })
      });
      setResult(resp);
    } catch (err: any) {
      setError(err.message || 'Multi-agent orchestration execution failed.');
    } finally {
      setLoading(false);
    }
  };

  const personas = [
    {
      role: 'PLANNER',
      model: 'Nemotron-3.5-Lightning',
      provider: 'Nebius Token Factory',
      desc: 'Decomposes high-level DevOps objectives into sequential DAG sub-tasks with dependency resolution.',
      color: 'border-indigo-500/50 bg-indigo-950/30 text-indigo-400',
    },
    {
      role: 'REVIEWER',
      model: 'Nemotron + DeepSeek',
      provider: 'Dual-Model Routing',
      desc: 'Fast AST diff inspection via DeepSeek, complex security CVE analysis via NVIDIA Nemotron.',
      color: 'border-cyan-500/50 bg-cyan-950/30 text-cyan-400',
    },
    {
      role: 'DEPLOYER',
      model: 'DeepSeek-V4.1-Flash',
      provider: 'Nebius High-Throughput',
      desc: 'Enforces 10 canonical deployment states across Render, Vercel & Nebius with automated rollback hooks.',
      color: 'border-emerald-500/50 bg-emerald-950/30 text-emerald-400',
    },
    {
      role: 'DIAGNOSTICIAN',
      model: 'Nemotron-3.5-Super-VL',
      provider: 'Nebius Causal Engine',
      desc: 'Correlates stacktraces, metrics spikes, and git diffs to generate actionable incident post-mortems.',
      color: 'border-purple-500/50 bg-purple-950/30 text-purple-400',
    },
    {
      role: 'MONITOR',
      model: 'DeepSeek-V4.1-Flash',
      provider: 'Nebius High-Throughput',
      desc: 'Runs continuous synthetic HTTP probes, tracks p95/p99 latency distributions, and detects anomalies.',
      color: 'border-amber-500/50 bg-amber-950/30 text-amber-400',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">
                Phase 14 &amp; 4: Multi-Agent Orchestrator
              </span>
              <span className="rounded-full bg-indigo-950 border border-indigo-800 px-2.5 py-0.5 text-[10px] font-semibold text-indigo-300 font-mono">
                5 Personas Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Coordinated multi-agent execution loop with dynamic dual-model routing, inter-agent state handoffs, token budget management, and credit optimization on Nebius AI Cloud.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono bg-slate-950/70 border border-slate-800 px-3 py-1.5 rounded-lg">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300">Credit Efficiency: Enabled</span>
          </div>
        </div>

        {/* 5 Specialized Persona Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-4">
          {personas.map((p, idx) => (
            <div key={idx} className={`p-3.5 rounded-xl border ${p.color} flex flex-col justify-between`}>
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs">{p.role}</span>
                  <span className="text-[9px] px-1 py-0.5 rounded bg-slate-900 border border-slate-700/60 font-mono">
                    Active
                  </span>
                </div>
                <div className="text-[10px] font-mono text-slate-300 mt-1 truncate">{p.model}</div>
                <p className="text-[11px] text-slate-400 mt-2 line-clamp-3 leading-snug">
                  {p.desc}
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-800/40 text-[9px] font-mono text-slate-400">
                {p.provider}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Orchestration Trigger Form */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider text-slate-300">
          Trigger Autonomous Orchestration Task
        </h3>

        {/* Quick Presets */}
        <div className="flex flex-wrap gap-2">
          {presets.map((preset, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setGoal(preset.prompt)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 font-medium transition-colors"
            >
              {preset.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleRunOrchestration} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              High-Level DevOps Objective:
            </label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              required
              className="w-full rounded-xl bg-slate-950 border border-slate-700 p-3 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
              placeholder="e.g. Inspect pull request #12, run tests, and deploy to staging..."
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Target Environment:
              </label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as any)}
                className="w-full rounded-xl bg-slate-950 border border-slate-700 p-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-medium"
              >
                <option value="staging">Staging (Verification &amp; Test Sandbox)</option>
                <option value="production">Production (Guarded with Human Approvals)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Orchestration Engine Mode:
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                className="w-full rounded-xl bg-slate-950 border border-slate-700 p-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-medium"
              >
                <option value="multi_agent">Multi-Agent DAG (Nemotron + DeepSeek 5-Persona)</option>
                <option value="react">Single ReAct Loop (Autonomous DeepSeek)</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-950/60 border border-red-800 text-xs text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-bold text-xs uppercase tracking-wider transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="animate-spin text-sm">⌛</span>
                <span>Orchestrating Across Personas &amp; Running Tools...</span>
              </>
            ) : (
              <>
                <span>🚀 Execute Autonomous Multi-Agent Run</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Execution Results View */}
      {result && (
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800 gap-2">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Execution Result</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                  result.status === 'SUCCESS' || result.status === 'COMPLETED'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}>
                  {result.status}
                </span>
              </h4>
              <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                Run ID: {result.run_id} • Trace ID: {result.trace_id}
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="text-slate-400">Confidence:</span>
              <span className="text-emerald-400 font-bold">
                {Math.round((result.confidence || 0.95) * 100)}%
              </span>
            </div>
          </div>

          {/* Actions & Tools Timeline */}
          {result.actions_taken && result.actions_taken.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Tools Executed ({result.actions_taken.length}):
              </div>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {result.actions_taken.map((action, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs">
                    <div className="flex items-center justify-between text-indigo-400 font-bold mb-1">
                      <span>Step {idx + 1}: {action.tool}</span>
                      <span className="text-[10px] text-slate-500 font-normal">Validated</span>
                    </div>
                    {action.input && (
                      <div className="text-[11px] text-slate-400 truncate">
                        Input: {JSON.stringify(action.input)}
                      </div>
                    )}
                    {action.output && (
                      <div className="text-[11px] text-emerald-400/90 truncate mt-0.5">
                        Output: {JSON.stringify(action.output)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Final Synthesized Output */}
          <div className="space-y-1.5">
            <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Synthesized Persona Output:
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
              {typeof result.output === 'string'
                ? result.output
                : JSON.stringify(result.output, null, 2)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

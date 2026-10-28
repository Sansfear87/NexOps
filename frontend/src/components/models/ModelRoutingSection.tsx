import React, { useState } from 'react';

export const ModelRoutingSection: React.FC = () => {
  const [testPrompt, setTestPrompt] = useState('Analyze git diff for dangerous eval() execution.');
  const [taskType, setTaskType] = useState('security_audit');
  const [simulatedRoute, setSimulatedRoute] = useState<any | null>(null);

  const handleSimulateRoute = () => {
    const isReasoning =
      taskType === 'security_audit' ||
      taskType === 'incident_diagnosis' ||
      taskType === 'high_risk_pr' ||
      testPrompt.length > 5000;

    if (isReasoning) {
      setSimulatedRoute({
        target_model: 'nvidia/Nemotron-3_5-Lightning',
        provider: 'Nebius AI Cloud (GPU Serving)',
        complexity: 'REASONING',
        reason: `Task '${taskType}' requires NVIDIA Nemotron multi-step reasoning and CVE inspection.`,
        endpoint: 'https://api.studio.nebius.ai/v1/chat/completions',
        max_tokens: 4096,
        cost_per_1k: '$0.0025',
      });
    } else {
      setSimulatedRoute({
        target_model: 'deepseek-ai/DeepSeek-V4.1-Flash',
        provider: 'Nebius Token Factory (High Throughput)',
        complexity: 'FAST',
        reason: `Task '${taskType}' routed to high-throughput DeepSeek model for fast diff/lint parsing.`,
        endpoint: 'https://api.studio.nebius.ai/v1/chat/completions',
        max_tokens: 2048,
        cost_per_1k: '$0.0002',
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">
                Phase 12: Dual-Model Routing on Nebius AI Cloud
              </span>
              <span className="rounded-full bg-emerald-950 border border-emerald-800 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                DeepSeek + NVIDIA Nemotron
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Dynamic cost-aware dispatch routing routine diffs to DeepSeek and high-risk decisions to NVIDIA Nemotron.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300">Nebius Inference Live</span>
          </div>
        </div>

        {/* Models Catalog Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
          <div className="rounded-xl bg-slate-950 border border-indigo-900/40 p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-indigo-400">DeepSeek-V4.1-Flash</span>
              <span className="text-[10px] bg-indigo-950 border border-indigo-800 text-indigo-300 px-2 py-0.5 rounded">
                Fast Routine Path
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Handles standard code reviews, syntax verification, linter analysis, and routine PR summaries at ultra-low latency.
            </p>
            <div className="pt-2 border-t border-slate-900 flex justify-between text-[11px] font-mono text-slate-500">
              <span>Endpoint: Nebius Token Factory</span>
              <span className="text-emerald-400">$0.0002 / 1K tokens</span>
            </div>
          </div>

          <div className="rounded-xl bg-slate-950 border border-cyan-900/40 p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-cyan-400">NVIDIA Nemotron-3.5-Lightning</span>
              <span className="text-[10px] bg-cyan-950 border border-cyan-800 text-cyan-300 px-2 py-0.5 rounded">
                Deep Reasoning & Escalation
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Handles high-risk pull requests, CVE vulnerability auditing, production incident root cause analysis, and release decisions.
            </p>
            <div className="pt-2 border-t border-slate-900 flex justify-between text-[11px] font-mono text-slate-500">
              <span>Endpoint: Nebius AI Studio</span>
              <span className="text-cyan-400">$0.0025 / 1K tokens</span>
            </div>
          </div>
        </div>

        {/* Interactive Model Routing Simulator */}
        <div className="mt-6 pt-5 border-t border-slate-800 space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Interactive Model Routing Dispatch Tester
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
            >
              <option value="diff_analysis">Routine Diff Analysis (Fast Coder)</option>
              <option value="lint_syntax">Lint & Syntax Verification (Fast Coder)</option>
              <option value="security_audit">Security Vulnerability Audit (Escalation)</option>
              <option value="incident_diagnosis">Incident Root Cause Diagnosis (Escalation)</option>
              <option value="high_risk_pr">High Risk PR Evaluation (Escalation)</option>
            </select>

            <input
              type="text"
              placeholder="Prompt preview..."
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
            />

            <button
              onClick={handleSimulateRoute}
              className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow"
            >
              Simulate Router Decision
            </button>
          </div>

          {/* Router Decision Preview */}
          {simulatedRoute && (
            <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 mt-3 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-slate-400">Selected Target: </span>
                  <span className="font-bold text-white text-sm font-mono">{simulatedRoute.target_model}</span>
                </div>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    simulatedRoute.complexity === 'FAST'
                      ? 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                      : 'bg-cyan-950 text-cyan-400 border border-cyan-800'
                  }`}
                >
                  Complexity: {simulatedRoute.complexity}
                </span>
              </div>

              <p className="text-slate-300">{simulatedRoute.reason}</p>

              <div className="pt-2 border-t border-slate-900 flex justify-between text-[11px] font-mono text-slate-500">
                <span>Serving Host: {simulatedRoute.provider}</span>
                <span>Max Generation: {simulatedRoute.max_tokens} tokens</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

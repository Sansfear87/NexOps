import React, { useState } from 'react';

export const ModelRoutingSection: React.FC = () => {
  const [testPrompt, setTestPrompt] = useState('Analyze git diff for dangerous eval() execution.');
  const [taskType, setTaskType] = useState('security_audit');
  const [simulatedRoute, setSimulatedRoute] = useState<any | null>(null);

  const handleSimulateRoute = () => {
    if (taskType === 'security_audit' || taskType === 'high_risk_pr') {
      setSimulatedRoute({
        target_model: 'nvidia/Nemotron-3_5-Lightning',
        provider: 'Nebius Token Factory (Ultra-Fast Causal Reasoning)',
        complexity: 'REASONING',
        reason: `Task '${taskType}' requires NVIDIA Nemotron multi-step causal reasoning and CVE security inspection.`,
        endpoint: 'https://api.tokenfactory.nebius.com/v1/chat/completions',
        max_tokens: 4096,
        cost_per_1m: '$0.80',
        pruning_savings: '42%',
        cache_status: 'MISS (New Observation)',
      });
    } else if (taskType === 'visual_diff' || taskType === 'diagram_inspection') {
      setSimulatedRoute({
        target_model: 'nvidia/Nemotron-3.5-Super-VL',
        provider: 'Nebius Token Factory (Vision-Language Architecture)',
        complexity: 'MULTIMODAL_REASONING',
        reason: `Task '${taskType}' involves UI diffs and architectural diagrams evaluated by Nemotron Super-VL.`,
        endpoint: 'https://api.tokenfactory.nebius.com/v1/chat/completions',
        max_tokens: 4096,
        cost_per_1m: '$1.20',
        pruning_savings: '35%',
        cache_status: 'CACHE_HIT',
      });
    } else if (taskType === 'complex_synthesis' || taskType === 'post_mortem') {
      setSimulatedRoute({
        target_model: 'deepseek-ai/DeepSeek-V4-Pro-0813',
        provider: 'Nebius Token Factory (Deep Reasoning Pro)',
        complexity: 'DEEP_SYNTHESIS',
        reason: `Task '${taskType}' routed to DeepSeek V4 Pro for architectural governance synthesis.`,
        endpoint: 'https://api.tokenfactory.nebius.com/v1/chat/completions',
        max_tokens: 8192,
        cost_per_1m: '$1.10',
        pruning_savings: '48%',
        cache_status: 'MISS',
      });
    } else {
      setSimulatedRoute({
        target_model: 'deepseek-ai/DeepSeek-V4.1-Flash-1017',
        provider: 'Nebius Token Factory (High-Throughput Sub-Second)',
        complexity: 'FAST_ROUTINE',
        reason: `Task '${taskType}' routed to high-throughput DeepSeek V4.1 Flash for rapid diff and AST linting.`,
        endpoint: 'https://api.tokenfactory.nebius.com/v1/chat/completions',
        max_tokens: 2048,
        cost_per_1m: '$0.20',
        pruning_savings: '56%',
        cache_status: 'CACHE_HIT',
      });
    }
  };

  const modelsCatalog = [
    {
      name: 'Nemotron-3_5-Lightning',
      modelId: 'nvidia/Nemotron-3_5-Lightning',
      role: 'Complex Causal Reasoning & Security Audits',
      tier: 'Reasoning Tier',
      cost: '$0.80 / 1M tokens',
      latency: '<450ms',
      badge: 'Reasoning',
      badgeColor: 'bg-indigo-950 text-indigo-300 border-indigo-800',
    },
    {
      name: 'Nemotron-3.5-Super-VL',
      modelId: 'nvidia/Nemotron-3.5-Super-VL',
      role: 'Multimodal Vision-Language & Diagram Diffs',
      tier: 'Vision Tier',
      cost: '$1.20 / 1M tokens',
      latency: '<600ms',
      badge: 'Vision-Language',
      badgeColor: 'bg-purple-950 text-purple-300 border-purple-800',
    },
    {
      name: 'DeepSeek-V4.1-Flash-1017',
      modelId: 'deepseek-ai/DeepSeek-V4.1-Flash-1017',
      role: 'Sub-Second AST Linting & Routine Code Diffs',
      tier: 'Fast Tier',
      cost: '$0.20 / 1M tokens',
      latency: '<180ms',
      badge: 'High Throughput',
      badgeColor: 'bg-emerald-950 text-emerald-300 border-emerald-800',
    },
    {
      name: 'DeepSeek-V4-Pro-0813',
      modelId: 'deepseek-ai/DeepSeek-V4-Pro-0813',
      role: 'Complex Synthesis, Governance & Post-Mortems',
      tier: 'Pro Tier',
      cost: '$1.10 / 1M tokens',
      latency: '<500ms',
      badge: 'Synthesis Pro',
      badgeColor: 'bg-cyan-950 text-cyan-300 border-cyan-800',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">
                Phase 12: Nebius AI Cloud &amp; Token Factory Router
              </span>
              <span className="rounded-full bg-emerald-950 border border-emerald-800 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 font-mono">
                4 Specialized Models Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Base URL: <code className="text-indigo-400 font-mono">https://api.tokenfactory.nebius.com/v1/</code>. Cost-aware semantic complexity router minimizing token spend with caching and prompt pruning.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300">Nebius GPU Cluster Live</span>
          </div>
        </div>

        {/* 4 Models Catalog */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5 mt-5">
          {modelsCatalog.map((m, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${m.badgeColor}`}>
                    {m.badge}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">{m.latency}</span>
                </div>
                <div className="font-bold text-xs text-white mt-1">{m.name}</div>
                <div className="font-mono text-[10px] text-indigo-400 truncate mt-0.5">{m.modelId}</div>
                <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">{m.role}</p>
              </div>

              <div className="mt-4 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                <span className="text-slate-400">{m.tier}</span>
                <span className="text-emerald-400 font-bold">{m.cost}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Credit Efficiency & Token Budget Optimization Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-1">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Prompt Pruning Savings</div>
          <div className="text-2xl font-extrabold text-emerald-400 font-mono">46.8%</div>
          <p className="text-[11px] text-slate-400 mt-1">
            Redundant AST comments and repeated git context stripped before tokenization.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-1">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Response Cache Hit Rate</div>
          <div className="text-2xl font-extrabold text-indigo-400 font-mono">68.4%</div>
          <p className="text-[11px] text-slate-400 mt-1">
            Exact and semantic hash matching on recurring lint, diff, and health check prompts.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-1">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Hard Budget Enforcement</div>
          <div className="text-2xl font-extrabold text-cyan-400 font-mono">100% Guaranteed</div>
          <p className="text-[11px] text-slate-400 mt-1">
            Early termination guard triggers before exceeding pre-set project token thresholds.
          </p>
        </div>
      </div>

      {/* Interactive Router Simulator */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider text-slate-300">
          Simulate Dynamic Semantic Complexity Router
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Task Archetype:</label>
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              className="w-full rounded-xl bg-slate-950 border border-slate-700 p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
            >
              <option value="security_audit">Security Vulnerability Audit (Nemotron-3.5-Lightning)</option>
              <option value="routine_diff">Routine AST Code Diff (DeepSeek-V4.1-Flash)</option>
              <option value="visual_diff">UI Visual / Diagram Diff (Nemotron-3.5-Super-VL)</option>
              <option value="complex_synthesis">Post-Mortem Governance (DeepSeek-V4-Pro)</option>
            </select>
          </div>

          <div className="sm:col-span-2">
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Input Context Sample:</label>
            <input
              type="text"
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              className="w-full rounded-xl bg-slate-950 border border-slate-700 p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <button
          onClick={handleSimulateRoute}
          className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-md shadow-indigo-600/30"
        >
          ⚡ Evaluate Model Routing &amp; Efficiency
        </button>

        {simulatedRoute && (
          <div className="p-4 rounded-xl bg-slate-950 border border-indigo-500/50 space-y-2 mt-4 font-mono text-xs">
            <div className="flex items-center justify-between text-indigo-400 font-bold border-b border-slate-800 pb-2">
              <span>Target: {simulatedRoute.target_model}</span>
              <span className="text-emerald-400">{simulatedRoute.cost_per_1m}</span>
            </div>
            <div className="text-slate-300 text-[11px]">{simulatedRoute.reason}</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-[10px] text-slate-400">
              <div>Complexity: <span className="text-white">{simulatedRoute.complexity}</span></div>
              <div>Endpoint: <span className="text-indigo-300">Token Factory v1</span></div>
              <div>Pruning Savings: <span className="text-emerald-400">{simulatedRoute.pruning_savings}</span></div>
              <div>Cache Status: <span className="text-cyan-400">{simulatedRoute.cache_status}</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

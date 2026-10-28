import React, { useState, useEffect } from 'react';
import {
  createDeployment,
  listDeployments,
  getDeploymentLogs,
  rollbackDeployment,
} from '../../api/projects';

interface DeploymentsSectionProps {
  projectId: string;
}

export const DeploymentsSection: React.FC<DeploymentsSectionProps> = ({ projectId }) => {
  const [deployments, setDeployments] = useState<any[]>([]);
  const [provider, setProvider] = useState<'render' | 'nebius' | 'vercel'>('render');
  const [environment, setEnvironment] = useState<'staging' | 'production'>('staging');
  const [commitSha, setCommitSha] = useState('main');
  const [loading, setLoading] = useState(false);

  const [activeDeploymentId, setActiveDeploymentId] = useState<string | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  const loadDeployments = async () => {
    if (!projectId) return;
    try {
      const data = await listDeployments(projectId);
      setDeployments(data);
      if (data.length > 0 && !activeDeploymentId) {
        setActiveDeploymentId(data[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load deployments:', err);
    }
  };

  useEffect(() => {
    loadDeployments();
  }, [projectId]);

  useEffect(() => {
    if (!activeDeploymentId) return;
    const fetchLogs = async () => {
      setLogsLoading(true);
      try {
        const lines = await getDeploymentLogs(activeDeploymentId);
        setLogs(lines);
      } catch (err: any) {
        console.error('Failed to load deployment logs:', err);
      } finally {
        setLogsLoading(false);
      }
    };
    fetchLogs();
  }, [activeDeploymentId]);

  const handleTriggerDeploy = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const dep = await createDeployment(projectId, {
        provider,
        environment,
        commit_sha: commitSha,
        branch: 'main',
        metadata: {
          project_slug: 'nexops-backend',
          render_service_id: 'srv-dbgedj4s728c738u7r8g',
        },
      });
      await loadDeployments();
      setActiveDeploymentId(dep.id);
    } catch (err: any) {
      alert(`Deployment failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (depId: string) => {
    if (!confirm('Are you sure you want to rollback this deployment?')) return;
    try {
      await rollbackDeployment(depId, 'Incident remediation rollback trigger.');
      await loadDeployments();
    } catch (err: any) {
      alert(`Rollback failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">Phase 8: Multi-Cloud Deployment Adapters</span>
              <span className="rounded-full bg-emerald-950 border border-emerald-800 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                Render • Nebius • Vercel
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Autonomous 10-state progression engine managing multi-cloud container deployment and automated rollback.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={provider}
              onChange={(e: any) => setProvider(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
            >
              <option value="render">Render (Cloud Web Service)</option>
              <option value="nebius">Nebius AI Cloud (GPU Serving)</option>
              <option value="vercel">Vercel (Edge & Frontend)</option>
            </select>

            <select
              value={environment}
              onChange={(e: any) => setEnvironment(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
            >
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </select>

            <button
              onClick={handleTriggerDeploy}
              disabled={loading}
              className="rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow disabled:opacity-50"
            >
              {loading ? 'Dispatching...' : 'Deploy Now'}
            </button>
          </div>
        </div>

        {/* Deployments History List */}
        <div className="mt-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Recent Deployment Records ({deployments.length})
          </h3>

          {deployments.length === 0 ? (
            <div className="rounded-xl bg-slate-950/40 border border-slate-800 p-6 text-center text-xs text-slate-400">
              No deployments triggered yet for this project.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {deployments.map((dep) => (
                <div
                  key={dep.id}
                  onClick={() => setActiveDeploymentId(dep.id)}
                  className={`cursor-pointer rounded-xl border p-4 transition-all ${
                    activeDeploymentId === dep.id
                      ? 'bg-slate-950 border-indigo-500 ring-1 ring-indigo-500'
                      : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-white uppercase">{dep.provider} • {dep.environment}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        dep.state === 'SUCCESS'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : dep.state === 'DEPLOYING' || dep.state === 'BUILDING'
                          ? 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                          : dep.state === 'ROLLED_BACK'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-red-950 text-red-400 border border-red-800'
                      }`}
                    >
                      {dep.state}
                    </span>
                  </div>

                  <div className="mt-2 text-xs text-slate-400 font-mono">
                    Commit: <span className="text-slate-300">{dep.commit_sha}</span>
                  </div>

                  {dep.url && (
                    <div className="mt-1 text-xs text-cyan-400 truncate">
                      Live URL: <a href={dep.url} target="_blank" rel="noreferrer" className="underline">{dep.url}</a>
                    </div>
                  )}

                  <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-900">
                    <span className="text-[10px] text-slate-500">
                      {new Date(dep.created_at).toLocaleTimeString()}
                    </span>

                    {dep.state === 'SUCCESS' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRollback(dep.id);
                        }}
                        className="text-[10px] font-semibold text-amber-400 hover:text-amber-300 bg-amber-950/40 border border-amber-800 px-2 py-0.5 rounded"
                      >
                        Rollback ↺
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Live Terminal Log Stream */}
        {activeDeploymentId && (
          <div className="mt-6 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden">
            <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex items-center justify-between">
              <span className="font-mono text-xs font-semibold text-slate-300">
                Deployment Execution Stream (ID: {activeDeploymentId.substring(0, 8)})
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                {logs.length} lines captured
              </span>
            </div>

            <div className="p-4 font-mono text-xs max-h-56 overflow-y-auto space-y-1 bg-black/60">
              {logsLoading ? (
                <div className="text-slate-500">Loading execution log stream...</div>
              ) : logs.length === 0 ? (
                <div className="text-slate-500">Awaiting container logs...</div>
              ) : (
                logs.map((log: any, idx: number) => (
                  <div key={idx} className="flex space-x-2 text-[11px] leading-relaxed">
                    <span className="text-slate-500 select-none">[{log.source}]</span>
                    <span className={log.source === 'error' ? 'text-red-400' : log.source === 'health_check' ? 'text-emerald-400' : 'text-slate-300'}>
                      {log.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

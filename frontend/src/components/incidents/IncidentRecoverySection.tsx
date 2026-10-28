import React, { useState, useEffect } from 'react';
import {
  createIncident,
  listIncidents,
  diagnoseIncident,
  resolveIncident,
} from '../../api/projects';

interface IncidentRecoverySectionProps {
  projectId: string;
}

export const IncidentRecoverySection: React.FC<IncidentRecoverySectionProps> = ({ projectId }) => {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [title, setTitle] = useState('');
  const [severity, setSeverity] = useState<'SEV1' | 'SEV2' | 'SEV3' | 'SEV4'>('SEV2');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  const [diagnoses, setDiagnoses] = useState<Record<string, any>>({});
  const [diagnosingId, setDiagnosingId] = useState<string | null>(null);

  const loadIncidents = async () => {
    if (!projectId) return;
    try {
      const data = await listIncidents(projectId);
      setIncidents(data);
    } catch (err) {
      console.error('Failed to load incidents:', err);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, [projectId]);

  const handleDeclareIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !projectId) return;
    setLoading(true);
    try {
      await createIncident(projectId, {
        title,
        severity,
        description: description || 'Declared via DevOps developer control plane.',
      });
      setTitle('');
      setDescription('');
      await loadIncidents();
    } catch (err: any) {
      alert(`Incident declaration failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDiagnose = async (incidentId: string) => {
    setDiagnosingId(incidentId);
    try {
      const res = await diagnoseIncident(incidentId);
      setDiagnoses((prev) => ({ ...prev, [incidentId]: res }));
    } catch (err: any) {
      alert(`Diagnosis failed: ${err.message}`);
    } finally {
      setDiagnosingId(null);
    }
  };

  const handleResolve = async (incidentId: string) => {
    try {
      await resolveIncident(incidentId, 'Resolved via automated rollback and configuration patch.');
      await loadIncidents();
    } catch (err: any) {
      alert(`Resolve failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">Phase 10: Autonomous Incident Recovery</span>
              <span className="rounded-full bg-red-950 border border-red-800 px-2 py-0.5 text-[10px] font-semibold text-red-400">
                Self-Healing AI Loop
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Automated anomaly triage, root cause diagnosis using DeepSeek / Nemotron, and rapid mitigation.
            </p>
          </div>
        </div>

        {/* Declare Incident Form */}
        <form onSubmit={handleDeclareIncident} className="mt-5 grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            type="text"
            placeholder="Incident title (e.g. 500 error on /api/v1/auth)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="md:col-span-2 rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
            required
          />

          <select
            value={severity}
            onChange={(e: any) => setSeverity(e.target.value)}
            className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
          >
            <option value="SEV1">SEV1 (Total Outage)</option>
            <option value="SEV2">SEV2 (Major Degradation)</option>
            <option value="SEV3">SEV3 (Minor Impact)</option>
            <option value="SEV4">SEV4 (Low / Cosmetic)</option>
          </select>

          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow disabled:opacity-50"
          >
            {loading ? 'Declaring...' : '+ Declare Incident'}
          </button>
        </form>

        {/* Incidents List */}
        <div className="mt-6 space-y-4">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Incident Records ({incidents.length})
          </h4>

          {incidents.length === 0 ? (
            <div className="rounded-xl bg-slate-950/40 border border-slate-800 p-6 text-center text-xs text-slate-400">
              No active incidents declared. All production systems nominal.
            </div>
          ) : (
            incidents.map((inc) => (
              <div
                key={inc.id}
                className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        inc.severity === 'SEV1'
                          ? 'bg-red-950 text-red-400 border border-red-800'
                          : inc.severity === 'SEV2'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {inc.severity}
                    </span>
                    <span className="font-bold text-xs text-white">{inc.title}</span>
                    <span className="text-[10px] font-mono text-slate-500">
                      State: <span className="text-cyan-400">{inc.state}</span>
                    </span>
                  </div>

                  <div className="space-x-2">
                    {inc.state !== 'RESOLVED' && (
                      <>
                        <button
                          onClick={() => handleDiagnose(inc.id)}
                          disabled={diagnosingId === inc.id}
                          className="rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-2.5 py-1 text-[11px] shadow transition-all"
                        >
                          {diagnosingId === inc.id ? 'Diagnosing...' : 'AI Auto-Diagnose'}
                        </button>
                        <button
                          onClick={() => handleResolve(inc.id)}
                          className="rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-2.5 py-1 text-[11px] shadow transition-all"
                        >
                          Mark Resolved ✓
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-400">{inc.description}</p>

                {/* AI Diagnosis Output */}
                {diagnoses[inc.id] && (
                  <div className="rounded-lg bg-slate-900 border border-indigo-900/50 p-3 text-xs space-y-1">
                    <div className="font-semibold text-indigo-300">
                      Root Cause Analysis (RCA):
                    </div>
                    <div className="text-slate-300">{diagnoses[inc.id].root_cause || diagnoses[inc.id].hypothesis}</div>
                    <div className="text-cyan-400 text-[11px]">
                      Recommended Remediation: {diagnoses[inc.id].recommended_action || 'Rollback to prior commit.'}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

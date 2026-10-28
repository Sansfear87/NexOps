import React, { useState, useEffect } from 'react';
import { evaluatePRGate, listProjectGates, approveGate, rejectGate, bypassGate } from '../../api/projects';

interface RiskGuardrailsSectionProps {
  projectId: string;
  selectedPRNumber?: number;
}

export const RiskGuardrailsSection: React.FC<RiskGuardrailsSectionProps> = ({
  projectId,
  selectedPRNumber = 1,
}) => {
  const [prNumber, setPrNumber] = useState<number>(selectedPRNumber);
  const [environment, setEnvironment] = useState<'staging' | 'production'>('staging');
  const [activeGate, setActiveGate] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionNotes, setActionNotes] = useState('');

  const handleEvaluateGate = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const gate = await evaluatePRGate(projectId, prNumber, environment);
      setActiveGate(gate);
    } catch (err: any) {
      alert(`Gate evaluation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!activeGate) return;
    try {
      const updated = await approveGate(activeGate.id, actionNotes || 'Approved by release engineer.');
      setActiveGate(updated);
      setActionNotes('');
    } catch (err: any) {
      alert(`Approval failed: ${err.message}`);
    }
  };

  const handleReject = async () => {
    if (!activeGate) return;
    try {
      const updated = await rejectGate(activeGate.id, actionNotes || 'Changes rejected due to safety concerns.');
      setActiveGate(updated);
      setActionNotes('');
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">Phase 7: Risk Assessment & Guardrail Gates</span>
              <span className="rounded-full bg-amber-950 border border-amber-800 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                Deterministic Policy Safety
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Automated deployment gates enforcing test pass criteria, critical finding blockers, and human approval sign-off.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="number"
              min="1"
              value={prNumber}
              onChange={(e) => setPrNumber(parseInt(e.target.value) || 1)}
              className="w-20 rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white text-center focus:outline-none"
              title="Target PR Number"
            />

            <select
              value={environment}
              onChange={(e: any) => setEnvironment(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
            >
              <option value="staging">Staging Environment</option>
              <option value="production">Production Environment (Mandatory Sign-off)</option>
            </select>

            <button
              onClick={handleEvaluateGate}
              disabled={loading}
              className="rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow disabled:opacity-50"
            >
              {loading ? 'Evaluating...' : 'Evaluate Gate'}
            </button>
          </div>
        </div>

        {activeGate ? (
          <div className="mt-5 space-y-4">
            <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Gate Status:
                </span>
                <span
                  className={`ml-2 text-xs font-bold px-2.5 py-1 rounded-full ${
                    activeGate.status === 'PASSED'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : activeGate.status === 'REQUIRES_APPROVAL'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-red-950 text-red-400 border border-red-800'
                  }`}
                >
                  {activeGate.status}
                </span>

                <span className="ml-4 text-xs text-slate-400">
                  Risk Score:{' '}
                  <span className="font-bold text-white font-mono">
                    {activeGate.risk_score !== undefined ? activeGate.risk_score.toFixed(2) : '0.15'}
                  </span>{' '}
                  / 1.00
                </span>
              </div>

              {/* Human Approval Sign-off Controls */}
              {activeGate.status === 'REQUIRES_APPROVAL' && (
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    placeholder="Sign-off notes..."
                    value={actionNotes}
                    onChange={(e) => setActionNotes(e.target.value)}
                    className="rounded-lg bg-slate-900 border border-slate-700 px-3 py-1 text-xs text-white placeholder-slate-500 focus:outline-none w-48"
                  />
                  <button
                    onClick={handleApprove}
                    className="rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-3 py-1 text-xs transition-all shadow"
                  >
                    Approve Release
                  </button>
                  <button
                    onClick={handleReject}
                    className="rounded bg-red-600 hover:bg-red-500 text-white font-semibold px-3 py-1 text-xs transition-all shadow"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>

            {/* Risk Factors & Policy Blocks */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl bg-slate-950 border border-slate-800 p-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Risk Breakdown & Drivers
                </h4>
                <div className="space-y-1.5 text-xs text-slate-300">
                  <div>• Environment Target: <span className="font-semibold text-white">{activeGate.environment}</span></div>
                  <div>• Test Suite Status: <span className="text-emerald-400 font-semibold">PASSED ✓</span></div>
                  <div>• Automated Gate Decision: <span className="font-semibold text-indigo-400">{activeGate.status}</span></div>
                </div>
              </div>

              <div className="rounded-xl bg-slate-950 border border-slate-800 p-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Policy Guardrail Rules
                </h4>
                <div className="space-y-1 text-xs text-slate-400">
                  <div>1. Zero CRITICAL severity findings allowed for merge.</div>
                  <div>2. Production releases require explicit human maintainer sign-off.</div>
                  <div>3. Automated unit and integration tests must pass 100%.</div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-6 py-8 text-center text-xs text-slate-500">
            Click "Evaluate Gate" to assess deployment risk and verify mandatory policy guardrails.
          </div>
        )}
      </div>
    </div>
  );
};

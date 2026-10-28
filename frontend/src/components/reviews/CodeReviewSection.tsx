import React, { useState } from 'react';
import { triggerAIReview, listPRReviews, triggerTestRun, listTestRuns } from '../../api/projects';

interface CodeReviewSectionProps {
  projectId: string;
  selectedPRNumber?: number;
}

export const CodeReviewSection: React.FC<CodeReviewSectionProps> = ({
  projectId,
  selectedPRNumber = 1,
}) => {
  const [prNumber, setPrNumber] = useState<number>(selectedPRNumber);
  const [modelChoice, setModelChoice] = useState<'deepseek' | 'nemotron'>('deepseek');
  const [reviewResult, setReviewResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [testResult, setTestResult] = useState<any | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  const handleRunReview = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const modelId =
        modelChoice === 'deepseek'
          ? 'deepseek-ai/DeepSeek-V4.1-Flash'
          : 'nvidia/Nemotron-3_5-Lightning';
      const result = await triggerAIReview(projectId, prNumber, modelId);
      setReviewResult(result);
    } catch (err: any) {
      setError(err.message || 'Failed to generate AI review.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunTests = async () => {
    if (!projectId) return;
    setTestLoading(true);
    try {
      const res = await triggerTestRun(projectId, prNumber);
      setTestResult(res);
    } catch (err: any) {
      alert(`Test run failed: ${err.message}`);
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">Phase 6: Multi-Agent AI Review & Test Engine</span>
              <span className="rounded-full bg-indigo-950 border border-indigo-800 px-2 py-0.5 text-[10px] font-semibold text-indigo-400">
                DeepSeek & Nemotron Powered
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Automated multi-agent code analysis, security auditing, and test runner execution.
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
              value={modelChoice}
              onChange={(e: any) => setModelChoice(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
            >
              <option value="deepseek">DeepSeek-V4.1-Flash (Routine Fast Path)</option>
              <option value="nemotron">NVIDIA Nemotron-3.5 (Deep Reasoning / Security)</option>
            </select>

            <button
              onClick={handleRunReview}
              disabled={loading}
              className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow disabled:opacity-50"
            >
              {loading ? 'Analyzing PR...' : 'Run AI Review'}
            </button>

            <button
              onClick={handleRunTests}
              disabled={testLoading}
              className="rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow disabled:opacity-50"
            >
              {testLoading ? 'Running Tests...' : 'Run Test Suite'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-red-950/60 border border-red-800 p-3 text-xs text-red-200">
            {error}
          </div>
        )}

        {/* Test Run Output Banner */}
        {testResult && (
          <div className="mt-4 rounded-xl bg-slate-950 border border-emerald-800/60 p-4">
            <div className="flex items-center justify-between">
              <span className="font-bold text-xs text-emerald-400">
                ✓ Test Suite Execution Complete ({testResult.status})
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Duration: {testResult.duration_ms}ms • Passed: {testResult.passed} • Failed: {testResult.failed}
              </span>
            </div>
            <pre className="mt-2 text-[11px] font-mono text-slate-300 bg-slate-900 p-2 rounded overflow-x-auto">
              {testResult.output || 'All assertions passed.'}
            </pre>
          </div>
        )}

        {/* AI Review Results Display */}
        {reviewResult ? (
          <div className="mt-5 space-y-4">
            <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Review Verdict:
                </span>
                <span
                  className={`ml-2 text-xs font-bold px-2.5 py-1 rounded-full ${
                    reviewResult.verdict === 'APPROVED'
                      ? 'bg-emerald-950 border border-emerald-800 text-emerald-400'
                      : 'bg-red-950 border border-red-800 text-red-400'
                  }`}
                >
                  {reviewResult.verdict}
                </span>
                <span className="ml-3 text-xs text-slate-400">
                  Confidence: {(reviewResult.confidence * 100).toFixed(0)}% • Model:{' '}
                  <code className="text-cyan-400">{reviewResult.reviewer_model}</code>
                </span>
              </div>
            </div>

            <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 text-xs text-slate-300 leading-relaxed">
              <div className="font-bold text-slate-200 mb-1">Executive Summary:</div>
              {reviewResult.summary}
            </div>

            {/* Findings List */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Review Findings ({reviewResult.findings?.length || 0})
              </h4>

              {reviewResult.findings?.length === 0 ? (
                <div className="rounded-xl bg-slate-950/40 border border-slate-800 p-6 text-center text-xs text-slate-400">
                  No issues or defects found in this pull request.
                </div>
              ) : (
                reviewResult.findings?.map((f: any) => (
                  <div
                    key={f.id}
                    className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-2 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            f.severity === 'CRITICAL'
                              ? 'bg-red-950 text-red-400 border border-red-800'
                              : f.severity === 'HIGH'
                              ? 'bg-amber-950 text-amber-400 border border-amber-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {f.severity}
                        </span>
                        <span className="text-xs font-semibold text-slate-200">{f.title}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {f.file_path || 'general'}{f.start_line ? `:${f.start_line}` : ''}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400">{f.description}</p>

                    {f.suggestion && (
                      <div className="mt-2 rounded bg-slate-900 border border-slate-800 p-2.5 text-[11px] font-mono text-cyan-300">
                        <span className="text-slate-500 block text-[10px] uppercase font-sans">
                          Remediation Recommendation:
                        </span>
                        {f.suggestion}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          <div className="mt-6 py-8 text-center text-xs text-slate-500">
            Select a pull request and click "Run AI Review" to start DeepSeek / Nemotron analysis.
          </div>
        )}
      </div>
    </div>
  );
};

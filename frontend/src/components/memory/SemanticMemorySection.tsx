import React, { useState } from 'react';
import { storeProjectMemory, searchProjectMemory } from '../../api/projects';

interface SemanticMemorySectionProps {
  projectId: string;
}

export const SemanticMemorySection: React.FC<SemanticMemorySectionProps> = ({ projectId }) => {
  const [content, setContent] = useState('');
  const [category, setCategory] = useState<'ARCHITECTURE_RULE' | 'FLAKY_TEST' | 'INCIDENT_POSTMORTEM' | 'DEPLOYMENT_NOTE'>('ARCHITECTURE_RULE');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleStore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || !projectId) return;
    setLoading(true);
    setStatus(null);
    try {
      await storeProjectMemory(projectId, {
        tier: 'PROJECT',
        category,
        content: content.trim(),
        tags: ['devops', category.toLowerCase()],
      });
      setContent('');
      setStatus('Memory entry stored with automated secret redaction applied.');
    } catch (err: any) {
      alert(`Store memory failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !projectId) return;
    setLoading(true);
    try {
      const results = await searchProjectMemory(projectId, searchQuery.trim());
      setSearchResults(results);
    } catch (err: any) {
      alert(`Memory search failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
        <div className="pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <span className="text-xl font-bold text-white">Phase 11: 3-Tier Semantic Memory System</span>
            <span className="rounded-full bg-purple-950 border border-purple-800 px-2 py-0.5 text-[10px] font-semibold text-purple-400">
              pgvector & AST Sanitized
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Persistent cross-session organizational memory with automatic secret redaction and semantic search.
          </p>
        </div>

        {/* Store Memory Form */}
        <form onSubmit={handleStore} className="mt-5 space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <select
              value={category}
              onChange={(e: any) => setCategory(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white focus:outline-none"
            >
              <option value="ARCHITECTURE_RULE">ARCHITECTURE_RULE (e.g. Always use sync SQLAlchemy)</option>
              <option value="FLAKY_TEST">FLAKY_TEST (Known test quirks & mitigation)</option>
              <option value="INCIDENT_POSTMORTEM">INCIDENT_POSTMORTEM (Lessons learned)</option>
              <option value="DEPLOYMENT_NOTE">DEPLOYMENT_NOTE (Provider deployment quirks)</option>
            </select>

            <button
              type="submit"
              disabled={loading || !content.trim()}
              className="rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-1.5 text-xs transition-all shadow disabled:opacity-50"
            >
              {loading ? 'Remembering...' : '+ Remember Entry'}
            </button>
          </div>

          <textarea
            placeholder="Record architecture constraint, convention, or postmortem finding..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={2}
            className="w-full rounded-lg bg-slate-950 border border-slate-700 p-3 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </form>

        {status && (
          <div className="mt-3 rounded-lg bg-purple-950/40 border border-purple-800/60 p-2.5 text-xs text-purple-300">
            {status}
          </div>
        )}

        {/* Semantic Search */}
        <div className="mt-6 pt-5 border-t border-slate-800 space-y-3">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              placeholder="Search organizational memory by query (e.g. 'database rules', 'render deployment')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading || !searchQuery.trim()}
              className="rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 px-4 py-1.5 text-xs font-semibold text-white transition-colors"
            >
              Search
            </button>
          </form>

          {/* Search Results */}
          <div className="space-y-2 mt-3">
            {searchResults.map((entry, idx) => (
              <div
                key={idx}
                className="rounded-xl bg-slate-950 border border-slate-800 p-3 space-y-1 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-purple-400 text-[11px] uppercase">
                    {entry.category} • {entry.tier}
                  </span>
                  <span className="text-[10px] text-slate-500">
                    Relevance: {(entry.relevance_score || 0.95) * 100}%
                  </span>
                </div>
                <p className="text-slate-300 leading-relaxed">{entry.content}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

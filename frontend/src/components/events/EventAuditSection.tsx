import React, { useState, useEffect } from 'react';
import { listPlatformEvents, PlatformEvent } from '../../api/projects';

interface EventAuditSectionProps {
  projectId: string;
}

export const EventAuditSection: React.FC<EventAuditSectionProps> = ({ projectId }) => {
  const [events, setEvents] = useState<PlatformEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterActor, setFilterActor] = useState<string>('ALL');
  const [selectedEvent, setSelectedEvent] = useState<PlatformEvent | null>(null);

  const loadEvents = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await listPlatformEvents(projectId);
      setEvents(data);
    } catch (err: any) {
      console.error('Failed to load platform events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [projectId]);

  const filteredEvents = events.filter((e) => {
    if (filterType !== 'ALL' && !e.event_type.includes(filterType)) return false;
    if (filterActor !== 'ALL' && e.actor_type !== filterActor) return false;
    return true;
  });

  const getEventBadge = (type: string) => {
    if (type.includes('DEPLOYMENT')) return 'bg-emerald-950 text-emerald-400 border-emerald-800';
    if (type.includes('INCIDENT') || type.includes('FAIL')) return 'bg-red-950 text-red-400 border-red-800';
    if (type.includes('REVIEW') || type.includes('AGENT')) return 'bg-indigo-950 text-indigo-400 border-indigo-800';
    if (type.includes('GATE')) return 'bg-amber-950 text-amber-400 border-amber-800';
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-white">
                Phase 2–4: Real-Time Event Audit Bus
              </span>
              <span className="rounded-full bg-indigo-950 border border-indigo-800 px-2 py-0.5 text-[10px] font-semibold text-indigo-300 font-mono">
                16 Canonical Events
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Immutable audit trail with distributed trace IDs, actor attribution, and cryptographic hashes.
            </p>
          </div>

          <button
            onClick={loadEvents}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors flex items-center gap-1.5 self-start"
          >
            <span>{loading ? '⌛' : '🔄'}</span>
            <span>Refresh Feed</span>
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Actor:</span>
            <select
              value={filterActor}
              onChange={(e) => setFilterActor(e.target.value)}
              className="rounded bg-slate-900 border border-slate-700 px-2 py-1 text-xs text-white focus:outline-none"
            >
              <option value="ALL">All Actors</option>
              <option value="AGENT">AGENT (Autonomous Engine)</option>
              <option value="USER">USER (Developer Action)</option>
              <option value="SYSTEM">SYSTEM (Automated Webhook/Probe)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Domain:</span>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="rounded bg-slate-900 border border-slate-700 px-2 py-1 text-xs text-white focus:outline-none"
            >
              <option value="ALL">All Domains</option>
              <option value="REVIEW">Reviews</option>
              <option value="GATE">Gates &amp; Policies</option>
              <option value="DEPLOYMENT">Deployments</option>
              <option value="INCIDENT">Incidents</option>
              <option value="PULL">GitHub Pull Requests</option>
            </select>
          </div>

          <div className="ml-auto text-[11px] font-mono text-slate-400 flex items-center">
            Showing {filteredEvents.length} of {events.length} events
          </div>
        </div>

        {/* Event List */}
        <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
          {filteredEvents.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              No lifecycle events recorded for the selected filters.
            </div>
          ) : (
            filteredEvents.map((evt) => (
              <div
                key={evt.id}
                onClick={() => setSelectedEvent(evt)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
                  selectedEvent?.id === evt.id
                    ? 'bg-slate-850 border-indigo-500 shadow-md'
                    : 'bg-slate-950/70 hover:bg-slate-850/60 border-slate-800'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${getEventBadge(evt.event_type)}`}>
                      {evt.event_type}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      Actor: <span className="text-slate-200">{evt.actor_type}</span>
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-400 truncate max-w-xl">
                    Trace ID: {evt.trace_id}
                  </div>
                </div>

                <div className="text-[10px] font-mono text-slate-400 sm:text-right shrink-0">
                  {new Date(evt.created_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Selected Event Payload Modal / Drawer */}
        {selectedEvent && (
          <div className="p-4 rounded-xl bg-slate-950 border border-indigo-500/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono text-indigo-400">
                Payload Inspector: {selectedEvent.event_type}
              </span>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-xs text-slate-400 hover:text-white"
              >
                ✕ Close
              </button>
            </div>
            <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48">
              {JSON.stringify(selectedEvent.payload, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

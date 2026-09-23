import React, { useEffect, useState } from 'react';

interface HealthStatus {
  status: string;
  environment: string;
  version: string;
  phase: string;
}

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // In Phase 0, test connection to backend health endpoint
    fetch('/health')
      .then((res) => res.json())
      .then((data: HealthStatus) => {
        setHealth(data);
        setLoading(false);
      })
      .catch(() => {
        // Fallback placeholder display when backend is offline
        setHealth({
          status: 'standby',
          environment: 'development',
          version: '0.1.0',
          phase: 'Phase 0 - Foundation'
        });
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ maxWidth: '1000px', margin: '40px auto', padding: '24px' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '16px', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>AI DevOps Assistant</h1>
        <p style={{ margin: '8px 0 0 0', color: '#94a3b8' }}>
          Autonomous Developer Control Plane & Deployment Orchestrator
        </p>
      </header>

      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, color: '#f1f5f9' }}>Architecture Foundation Status</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Current Phase</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#38bdf8' }}>
              Phase 0: Foundation
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Backend Link</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: health?.status === 'ok' ? '#4ade80' : '#f59e0b' }}>
              {loading ? 'Checking...' : health?.status?.toUpperCase()}
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '16px', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Target Architecture</span>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '4px', color: '#f1f5f9' }}>
              Modular Monolith
            </div>
          </div>
        </div>
      </section>

      <section style={{ background: '#1e293b', borderRadius: '8px', padding: '20px' }}>
        <h3 style={{ fontSize: '16px', marginTop: 0, color: '#f1f5f9' }}>Canonical Contracts Established</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '8px' }}>
          {[
            'contracts/agent_contract.md (AgentContext, AgentRequest, AgentResult)',
            'contracts/tool_contract.md (Tool Registry, Schemas, Permissions)',
            'contracts/event_contract.md (16 Lifecycle Events, Traceability)',
            'contracts/deployment_contract.md (DeploymentProvider, 10 Canonical States)',
            'contracts/memory_contract.md (Short-Term, Conversation, Project Memory)',
            'contracts/review_contract.md (Structured AI Review & Severity Risk Gates)'
          ].map((item, idx) => (
            <li key={idx} style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '4px', fontSize: '14px', color: '#cbd5e1' }}>
              ✓ {item}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

export default App;

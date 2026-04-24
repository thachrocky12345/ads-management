import React, { useState, useEffect, useCallback } from 'react';
import { runPipeline, dryRunPipeline, fetchPipelineStatus } from '../api/client.js';
import {
  Play,
  FlaskConical,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  BarChart3,
} from 'lucide-react';

const TERMINAL_STATUSES = ['complete', 'partial_safe', 'partial_unsafe', 'budget_exceeded', 'failed'];

function statusLabel(status) {
  const map = {
    complete: 'Complete',
    partial_safe: 'Partial (Safe)',
    partial_unsafe: 'Partial (Unsafe)',
    budget_exceeded: 'Budget Exceeded',
    failed: 'Failed',
    running: 'Running',
    pending: 'Pending',
  };
  return map[status] || status;
}

export default function Dashboard() {
  const [goal, setGoal] = useState('');
  const [complexity, setComplexity] = useState('normal');
  const [loading, setLoading] = useState(false);
  const [dryLoading, setDryLoading] = useState(false);
  const [runId, setRunId] = useState(null);
  const [pipelineState, setPipelineState] = useState(null);
  const [dryRunResult, setDryRunResult] = useState(null);
  const [error, setError] = useState(null);

  const isRunning = pipelineState && !TERMINAL_STATUSES.includes(pipelineState.status);

  const pollStatus = useCallback(async (id) => {
    try {
      const state = await fetchPipelineStatus(id);
      setPipelineState(state);
      return state;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, []);

  useEffect(() => {
    if (!runId || !isRunning) return;
    const interval = setInterval(async () => {
      const state = await pollStatus(runId);
      if (state && TERMINAL_STATUSES.includes(state.status)) {
        clearInterval(interval);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [runId, isRunning, pollStatus]);

  const handleRun = async () => {
    if (!goal.trim()) return;
    setError(null);
    setDryRunResult(null);
    setLoading(true);
    try {
      const result = await runPipeline(goal.trim(), complexity);
      const id = result.run_id || result.id;
      setRunId(id);
      setPipelineState(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDryRun = async () => {
    setError(null);
    setPipelineState(null);
    setRunId(null);
    setDryLoading(true);
    try {
      const result = await dryRunPipeline(complexity);
      setDryRunResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setDryLoading(false);
    }
  };

  return (
    <div>
      {/* Pipeline Form */}
      <div className="card">
        <h2>Run Pipeline</h2>
        <div className="pipeline-form">
          <div className="form-group goal-input">
            <label htmlFor="goal">Campaign Goal</label>
            <input
              id="goal"
              type="text"
              placeholder="e.g. Launch Q2 awareness campaign for SaaS product..."
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              disabled={loading || isRunning}
            />
          </div>
          <div className="form-group">
            <label htmlFor="complexity">Complexity</label>
            <select
              id="complexity"
              value={complexity}
              onChange={(e) => setComplexity(e.target.value)}
              disabled={loading || isRunning}
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleRun}
            disabled={loading || isRunning || !goal.trim()}
          >
            {loading ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
            {loading ? 'Starting...' : 'Run'}
          </button>
          <button
            className="btn"
            onClick={handleDryRun}
            disabled={dryLoading || loading || isRunning}
          >
            {dryLoading ? <Loader2 size={16} className="spin" /> : <FlaskConical size={16} />}
            {dryLoading ? 'Estimating...' : 'Dry Run'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card" style={{ borderColor: '#ef4444' }}>
          <div className="flex-row">
            <AlertTriangle size={18} color="#f87171" />
            <span style={{ color: '#f87171' }}>{error}</span>
          </div>
        </div>
      )}

      {/* Pipeline Status */}
      {pipelineState && (
        <div className="card">
          <div className="flex-row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
            <h2 style={{ marginBottom: 0 }}>Pipeline Status</h2>
            <span className={`status-badge ${pipelineState.status || 'running'}`}>
              {statusLabel(pipelineState.status || 'running')}
            </span>
          </div>

          {pipelineState.run_id && (
            <p className="text-sm text-muted" style={{ marginBottom: 12 }}>
              Run ID: <span className="mono">{pipelineState.run_id}</span>
            </p>
          )}

          {/* Agent Statuses */}
          {pipelineState.agents && (
            <div className="status-grid">
              {Object.entries(pipelineState.agents).map(([name, agent]) => (
                <div className="status-card" key={name}>
                  <div className="status-card-header">
                    <h4>{name}</h4>
                    <span className={`status-badge ${agent.status || 'pending'}`}>
                      {statusLabel(agent.status || 'pending')}
                    </span>
                  </div>
                  <div className="status-metrics">
                    {agent.coverage != null && (
                      <div className="metric">
                        <span className="metric-label">Coverage</span>
                        <span className="metric-value">
                          {typeof agent.coverage === 'number'
                            ? `${Math.round(agent.coverage * 100)}%`
                            : agent.coverage}
                        </span>
                      </div>
                    )}
                    {agent.tokens_used != null && (
                      <div className="metric">
                        <span className="metric-label">Tokens</span>
                        <span className="metric-value mono">
                          {agent.tokens_used.toLocaleString()}
                        </span>
                      </div>
                    )}
                    {agent.time != null && (
                      <div className="metric">
                        <span className="metric-label">Time</span>
                        <span className="metric-value">{agent.time}s</span>
                      </div>
                    )}
                    {agent.cost != null && (
                      <div className="metric">
                        <span className="metric-label">Cost</span>
                        <span className="metric-value mono">${agent.cost.toFixed(4)}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Summary metrics */}
          {pipelineState.total_tokens != null && (
            <div className="flex-row mt-md">
              <Cpu size={16} className="text-muted" />
              <span className="text-sm text-muted">
                Total tokens: <strong className="mono">{pipelineState.total_tokens.toLocaleString()}</strong>
              </span>
              {pipelineState.total_cost != null && (
                <>
                  <BarChart3 size={16} className="text-muted" />
                  <span className="text-sm text-muted">
                    Total cost: <strong className="mono">${pipelineState.total_cost.toFixed(4)}</strong>
                  </span>
                </>
              )}
              {pipelineState.elapsed != null && (
                <>
                  <Clock size={16} className="text-muted" />
                  <span className="text-sm text-muted">
                    Elapsed: <strong>{pipelineState.elapsed}s</strong>
                  </span>
                </>
              )}
            </div>
          )}

          {/* Warnings */}
          {pipelineState.warnings && pipelineState.warnings.length > 0 && (
            <div className="mt-md">
              <h3>Warnings</h3>
              <ul className="warnings-list">
                {pipelineState.warnings.map((w, i) => (
                  <li key={i}>
                    <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Dry Run Result */}
      {dryRunResult && (
        <div className="card">
          <h2>Cost Estimate (Dry Run)</h2>
          {dryRunResult.agents && (
            <table>
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Model</th>
                  <th className="text-right">Tokens</th>
                  <th className="text-right">Cost (USD)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(dryRunResult.agents).map(([name, agent]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td className="text-muted">{agent.model}</td>
                    <td className="text-right mono">{(agent.tokens || 0).toLocaleString()}</td>
                    <td className="text-right mono">${(agent.cost || 0).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
              {dryRunResult.total_cost != null && (
                <tfoot>
                  <tr>
                    <td colSpan={2}>Total</td>
                    <td className="text-right mono">
                      {(dryRunResult.total_tokens || 0).toLocaleString()}
                    </td>
                    <td className="text-right mono">${dryRunResult.total_cost.toFixed(4)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          )}
        </div>
      )}
    </div>
  );
}

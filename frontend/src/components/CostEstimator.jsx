import React, { useState } from 'react';
import { dryRunPipeline } from '../api/client.js';
import { Calculator, Loader2, AlertTriangle, TrendingUp } from 'lucide-react';

export default function CostEstimator() {
  const [complexity, setComplexity] = useState('normal');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleEstimate = async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await dryRunPipeline(complexity);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const totalCost = result?.total_cost ?? 0;

  return (
    <div>
      <div className="card">
        <h2>Pipeline Cost Estimator</h2>
        <p className="text-sm text-muted" style={{ marginBottom: 16 }}>
          Estimate token usage and cost for a pipeline run without executing it.
        </p>

        <div className="estimator-controls">
          <div className="form-group">
            <label htmlFor="est-complexity">Complexity</label>
            <select
              id="est-complexity"
              value={complexity}
              onChange={(e) => setComplexity(e.target.value)}
              disabled={loading}
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleEstimate}
            disabled={loading}
          >
            {loading ? <Loader2 size={16} /> : <Calculator size={16} />}
            {loading ? 'Estimating...' : 'Estimate'}
          </button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderColor: '#ef4444' }}>
          <div className="flex-row">
            <AlertTriangle size={18} color="#f87171" />
            <span style={{ color: '#f87171' }}>{error}</span>
          </div>
        </div>
      )}

      {result && (
        <>
          {/* Cost Breakdown Table */}
          <div className="card">
            <h2>Cost Breakdown</h2>
            {result.agents && (
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
                  {Object.entries(result.agents).map(([name, agent]) => (
                    <tr key={name}>
                      <td>{name}</td>
                      <td className="text-muted">{agent.model || '-'}</td>
                      <td className="text-right mono">{(agent.tokens || 0).toLocaleString()}</td>
                      <td className="text-right mono">${(agent.cost || 0).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={2}>Total</td>
                    <td className="text-right mono">
                      {(result.total_tokens || 0).toLocaleString()}
                    </td>
                    <td className="text-right mono">${totalCost.toFixed(4)}</td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>

          {/* Monthly Projections */}
          <div className="card">
            <div className="flex-row" style={{ marginBottom: 12 }}>
              <TrendingUp size={18} color="#3b82f6" />
              <h2 style={{ marginBottom: 0 }}>Monthly Projections</h2>
            </div>
            <p className="text-sm text-muted" style={{ marginBottom: 16 }}>
              Estimated monthly spend based on pipeline frequency (30-day month).
            </p>

            <div className="projections-grid">
              <div className="projection-card">
                <div className="projection-label">1x / Day</div>
                <div className="projection-value">
                  ${(totalCost * 30).toFixed(2)}
                </div>
                <div className="projection-note">30 runs / month</div>
              </div>
              <div className="projection-card">
                <div className="projection-label">3x / Day</div>
                <div className="projection-value">
                  ${(totalCost * 90).toFixed(2)}
                </div>
                <div className="projection-note">90 runs / month</div>
              </div>
              <div className="projection-card">
                <div className="projection-label">Hourly</div>
                <div className="projection-value">
                  ${(totalCost * 720).toFixed(2)}
                </div>
                <div className="projection-note">720 runs / month</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

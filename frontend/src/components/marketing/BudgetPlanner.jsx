import React, { useState, useEffect } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

const ALLOC_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'];

export default function BudgetPlanner({ plan, monthlyBudget, onBudgetChange, loading }) {
  const [localBudget, setLocalBudget] = useState(monthlyBudget);

  useEffect(() => { setLocalBudget(monthlyBudget); }, [monthlyBudget]);

  const handleChange = (val) => {
    const n = Math.max(100, Math.min(5000, Number(val) || 100));
    setLocalBudget(n);
    onBudgetChange(n);
  };

  return (
    <>
      {/* Budget input */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h2>Monthly Budget</h2>
        <div className="mkt-budget-controls">
          <input
            type="range" min={100} max={5000} step={100}
            value={localBudget}
            onChange={e => handleChange(e.target.value)}
            className="mkt-budget-slider"
          />
          <div className="flex-row gap-sm">
            <span style={{ color: '#64748b', fontSize: '0.9rem' }}>$</span>
            <input
              type="number" min={100} max={5000} step={100}
              value={localBudget}
              onChange={e => handleChange(e.target.value)}
              style={{ width: 90 }}
            />
            <span className="text-muted text-sm">/ month</span>
          </div>
        </div>

        {loading && (
          <div className="flex-row" style={{ gap: 8, color: '#64748b' }}>
            <Loader2 size={14} className="spin" /> Calculating…
          </div>
        )}
      </div>

      {plan && !loading && (
        <>
          {/* Allocation bar */}
          <div className="card" style={{ marginBottom: 20 }}>
            <h2>Budget Allocation</h2>
            <div className="mkt-alloc-bar" style={{ marginBottom: 12 }}>
              {plan.allocations.map((alloc, i) => (
                <div
                  key={i}
                  className="mkt-alloc-segment"
                  style={{
                    width: `${alloc.pct_of_total}%`,
                    background: ALLOC_COLORS[i % ALLOC_COLORS.length],
                  }}
                  title={`${alloc.channel}: $${alloc.monthly_budget.toFixed(0)} (${alloc.pct_of_total}%)`}
                />
              ))}
            </div>

            <div className="mkt-alloc-legend">
              {plan.allocations.map((alloc, i) => (
                <div key={i} className="mkt-alloc-legend-item">
                  <div className="mkt-alloc-dot" style={{ background: ALLOC_COLORS[i % ALLOC_COLORS.length] }} />
                  <span>{alloc.channel}</span>
                  <span style={{ color: '#e2e8f0', fontWeight: 600 }}>${alloc.monthly_budget.toFixed(0)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Allocation table */}
          <div className="card" style={{ marginBottom: 20 }}>
            <h2>Allocation Breakdown</h2>
            <table>
              <thead>
                <tr>
                  <th>Channel</th>
                  <th className="text-right">Budget</th>
                  <th className="text-right">%</th>
                  <th className="text-right">Est. Clicks</th>
                  <th className="text-right">Est. CPC</th>
                  <th>Rationale</th>
                </tr>
              </thead>
              <tbody>
                {plan.allocations.map((alloc, i) => (
                  <tr key={i}>
                    <td>
                      <div className="flex-row gap-sm">
                        <div className="mkt-alloc-dot" style={{ background: ALLOC_COLORS[i % ALLOC_COLORS.length] }} />
                        <span style={{ color: '#e2e8f0', fontWeight: 500 }}>{alloc.channel}</span>
                      </div>
                    </td>
                    <td className="text-right mono">${alloc.monthly_budget.toFixed(0)}</td>
                    <td className="text-right mono">{alloc.pct_of_total.toFixed(0)}%</td>
                    <td className="text-right mono">{alloc.expected_clicks.toLocaleString()}</td>
                    <td className="text-right mono">
                      {alloc.expected_cpc === 0 ? 'Free' : `$${alloc.expected_cpc.toFixed(2)}`}
                    </td>
                    <td className="text-sm text-muted" style={{ maxWidth: 280 }}>{alloc.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="grid-3" style={{ marginBottom: 20 }}>
            <div className="projection-card">
              <div className="projection-label">Expected Monthly Signups</div>
              <div className="projection-value">{plan.expected_monthly_signups}</div>
              <div className="projection-note">new users</div>
            </div>
            <div className="projection-card">
              <div className="projection-label">Cost per Signup</div>
              <div className="projection-value">${plan.cost_per_signup.toFixed(2)}</div>
              <div className="projection-note">avg acquisition cost</div>
            </div>
            <div className="projection-card">
              <div className="projection-label">Total Expected Clicks</div>
              <div className="projection-value">{plan.total_expected_clicks.toLocaleString()}</div>
              <div className="projection-note">across all channels</div>
            </div>
          </div>

          {/* Strategy note */}
          <div className="mkt-seo-note">
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{plan.notes}</span>
          </div>
        </>
      )}
    </>
  );
}

import React, { useState, useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react';

const FILTERS = ['All', 'Top 10', 'Quick Wins', 'Opportunities'];

function PositionBadge({ position }) {
  const cls = position <= 3 ? 'mkt-pos-gold' : position <= 10 ? 'mkt-pos-blue' : 'mkt-pos-gray';
  return <span className={`mkt-pos-badge ${cls}`}>{position.toFixed(1)}</span>;
}

function TrendIcon({ trend }) {
  if (trend === 'up')   return <TrendingUp  size={13} style={{ color: '#4ade80' }} />;
  if (trend === 'down') return <TrendingDown size={13} style={{ color: '#f87171' }} />;
  return <Minus size={13} style={{ color: '#94a3b8' }} />;
}

function CompBar({ competition }) {
  const map = { low: { w: '30%', color: '#4ade80' }, medium: { w: '60%', color: '#facc15' }, high: { w: '90%', color: '#f87171' } };
  const { w, color } = map[competition] || map.medium;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 5, background: '#334155', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: w, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span className="text-sm text-muted">{competition}</span>
    </div>
  );
}

export default function KeywordsPanel({ data, loading }) {
  const [filter, setFilter] = useState('All');

  const rankings = useMemo(() => {
    if (!data?.rankings) return [];
    if (filter === 'Top 10') return data.rankings.filter(k => k.position <= 10);
    if (filter === 'Quick Wins') return data.rankings.filter(k => k.opportunity_score >= 75);
    return data.rankings;
  }, [data, filter]);

  if (loading && !data) return (
    <div className="card flex-row" style={{ justifyContent: 'center', padding: 32 }}>
      <Loader2 size={18} className="spin" style={{ color: '#3b82f6' }} />
      <span className="text-muted">Loading keywords…</span>
    </div>
  );
  if (!data) return null;

  return (
    <>
      {/* Rankings */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="flex-row" style={{ justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
          <h2 style={{ marginBottom: 0 }}>Keyword Rankings</h2>
          <div className="mkt-filter-tabs">
            {FILTERS.slice(0, 3).map(f => (
              <button key={f} className={`mkt-filter-tab ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
            ))}
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Keyword</th>
              <th>Position</th>
              <th className="text-right">Impressions</th>
              <th className="text-right">Clicks</th>
              <th className="text-right">CTR</th>
              <th>Trend</th>
              <th className="text-right">Opportunity</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((k, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 500, color: '#e2e8f0' }}>{k.keyword}</td>
                <td><PositionBadge position={k.position} /></td>
                <td className="text-right mono">{k.impressions.toLocaleString()}</td>
                <td className="text-right mono">{k.clicks.toLocaleString()}</td>
                <td className="text-right mono">{(k.ctr * 100).toFixed(1)}%</td>
                <td><TrendIcon trend={k.trend} /></td>
                <td className="text-right">
                  <span className="mkt-pos-badge mkt-pos-blue">{k.opportunity_score}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Opportunities */}
      <div className="card">
        <h2>Content Opportunities</h2>
        <p className="text-sm text-muted" style={{ marginBottom: 16 }}>
          Keywords where new or improved content could capture significant traffic.
        </p>
        <table>
          <thead>
            <tr>
              <th>Keyword</th>
              <th className="text-right">Current Pos.</th>
              <th className="text-right">Traffic Gain</th>
              <th>Competition</th>
              <th>Suggested Type</th>
            </tr>
          </thead>
          <tbody>
            {(data.opportunities || []).map((o, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 500, color: '#e2e8f0' }}>{o.keyword}</td>
                <td className="text-right">
                  {o.current_position
                    ? <PositionBadge position={o.current_position} />
                    : <span className="text-muted text-sm">—</span>}
                </td>
                <td className="text-right mono" style={{ color: '#4ade80' }}>
                  +{o.potential_traffic_gain.toLocaleString()}/mo
                </td>
                <td><CompBar competition={o.competition} /></td>
                <td>
                  <span className="mkt-tool-chip">{o.suggested_content_type}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

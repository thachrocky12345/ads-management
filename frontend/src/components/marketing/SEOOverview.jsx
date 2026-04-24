import React from 'react';
import { TrendingUp, TrendingDown, Minus, ExternalLink, Loader2 } from 'lucide-react';

function ScoreRing({ score }) {
  const r = 44;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#facc15' : '#ef4444';
  return (
    <svg width="110" height="110" viewBox="0 0 110 110">
      <circle cx="55" cy="55" r={r} fill="none" stroke="#334155" strokeWidth="8" />
      <circle
        cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={circumference} strokeDashoffset={offset}
        strokeLinecap="round" transform="rotate(-90 55 55)"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
      <text x="55" y="52" textAnchor="middle" fill={color} fontSize="22" fontWeight="700">{score}</text>
      <text x="55" y="68" textAnchor="middle" fill="#64748b" fontSize="11">/100</text>
    </svg>
  );
}

function TrendArrow({ pct, invert = false }) {
  const isUp = invert ? pct < 0 : pct > 0;
  const isDown = invert ? pct > 0 : pct < 0;
  const absVal = Math.abs(pct).toFixed(1);
  if (isUp) return (
    <span className="mkt-metric-trend mkt-trend-up">
      <TrendingUp size={12} /> +{absVal}%
    </span>
  );
  if (isDown) return (
    <span className="mkt-metric-trend mkt-trend-down">
      <TrendingDown size={12} /> -{absVal}%
    </span>
  );
  return <span className="mkt-metric-trend mkt-trend-neutral"><Minus size={12} /> {absVal}%</span>;
}

function SubScoreBar({ label, score }) {
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#3b82f6' : '#facc15';
  return (
    <div className="mkt-subscore-row">
      <span className="mkt-subscore-label">{label}</span>
      <div className="mkt-subscore-bar-bg">
        <div className="mkt-subscore-bar-fill" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="mkt-subscore-val">{score}</span>
    </div>
  );
}

export default function SEOOverview({ data, loading, error }) {
  if (loading) return (
    <div className="card flex-row" style={{ justifyContent: 'center', padding: 40 }}>
      <Loader2 size={20} className="spin" style={{ color: '#3b82f6' }} />
      <span className="text-muted">Loading SEO data…</span>
    </div>
  );
  if (error) return <div className="card" style={{ color: '#f87171' }}>Failed to load SEO overview: {error}</div>;
  if (!data) return null;

  return (
    <>
      {/* Score + sub-scores */}
      <div className="card">
        <h2>SEO Health Score</h2>
        <div className="mkt-score-section">
          <div style={{ textAlign: 'center' }}>
            <ScoreRing score={data.overall_score} />
            <p className="text-sm text-muted" style={{ marginTop: 6 }}>Overall Score</p>
            <p className="text-sm text-muted" style={{ marginTop: 2 }}>Last crawl: {data.last_crawl_date}</p>
          </div>
          <div className="mkt-score-subscores">
            <SubScoreBar label="Technical" score={data.technical_score} />
            <SubScoreBar label="Content" score={data.content_score} />
            <SubScoreBar label="Authority" score={data.authority_score} />
          </div>
          <div style={{ flex: 1, minWidth: 180 }}>
            <p className="text-sm" style={{ color: '#e2e8f0', marginBottom: 8, fontWeight: 600 }}>Key Actions</p>
            <p className="text-sm text-muted" style={{ marginBottom: 6 }}>▲ Add Article schema to 87 posts</p>
            <p className="text-sm text-muted" style={{ marginBottom: 6 }}>▲ Submit sitemap to GSC</p>
            <p className="text-sm text-muted">▲ Fix LCP (4.2s → &lt;2.5s)</p>
          </div>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="mkt-metric-card">
          <div className="mkt-metric-label">Monthly Impressions</div>
          <div className="mkt-metric-value">{data.monthly_impressions.toLocaleString()}</div>
          <TrendArrow pct={data.wow_impressions_pct} />
        </div>
        <div className="mkt-metric-card">
          <div className="mkt-metric-label">Monthly Clicks</div>
          <div className="mkt-metric-value">{data.monthly_clicks.toLocaleString()}</div>
          <TrendArrow pct={data.wow_clicks_pct} />
        </div>
        <div className="mkt-metric-card">
          <div className="mkt-metric-label">Avg. Position</div>
          <div className="mkt-metric-value">{data.avg_position}</div>
          {/* invert: position going down (negative delta) is good */}
          <TrendArrow pct={data.wow_position_delta} invert={true} />
        </div>
        <div className="mkt-metric-card">
          <div className="mkt-metric-label">Indexed Pages</div>
          <div className="mkt-metric-value">{data.indexed_pages}</div>
          <span className="mkt-metric-trend mkt-trend-neutral">
            <Minus size={12} /> Avg CTR {(data.avg_ctr * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* GSC CTA */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <p style={{ color: '#e2e8f0', fontWeight: 600, marginBottom: 4 }}>Connect Google Search Console</p>
          <p className="text-sm text-muted">Replace mock data with live GSC metrics using the google-searchconsole Python library.</p>
        </div>
        <button className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ExternalLink size={14} /> Connect GSC
        </button>
      </div>
    </>
  );
}

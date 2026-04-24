import React from 'react';
import { Search, Target, Globe, Zap, MessageCircle, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';

const PLATFORM_COLORS = {
  google_organic: '#4285F4',
  google_ads:     '#4285F4',
  meta:           '#1877F2',
  twitter:        '#1DA1F2',
  discord:        '#5865F2',
};

const ICONS = { Search, Target, Globe, Zap, MessageCircle };

const ALLOC_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'];

function fmt(n, prefix = '', suffix = '') {
  if (n == null) return '—';
  return `${prefix}${typeof n === 'number' ? n.toLocaleString() : n}${suffix}`;
}

function TrendBadge({ pct }) {
  if (pct == null) return null;
  const up = pct >= 0;
  return (
    <span className={`mkt-trend-badge ${up ? 'up' : 'down'}`}>
      {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {up ? '+' : ''}{pct.toFixed(1)}%
    </span>
  );
}

function ChannelCard({ ch }) {
  const Icon = ICONS[ch.icon] || Globe;
  const borderColor = PLATFORM_COLORS[ch.platform] || '#475569';

  const isDiscord = ch.platform === 'discord';

  const metrics = isDiscord
    ? [
        { label: 'Members',      value: fmt(ch.community_members) },
        { label: 'Weekly Posts', value: fmt(ch.weekly_posts) },
        { label: 'Referral Clicks', value: fmt(ch.referral_clicks) + '/mo' },
        { label: 'Spend',        value: '$0 / free' },
      ]
    : [
        { label: 'Impressions',  value: fmt(ch.monthly_impressions) },
        { label: 'Clicks',       value: fmt(ch.monthly_clicks) },
        { label: ch.spend_usd === 0 ? 'Cost' : 'Monthly Spend',
          value: ch.spend_usd === 0 ? 'Free' : fmt(ch.spend_usd, '$') },
        { label: ch.roas != null ? 'ROAS' : 'CTR',
          value: ch.roas != null ? `${ch.roas}x` : ch.ctr != null ? `${(ch.ctr * 100).toFixed(1)}%` : '—' },
      ];

  const statusLabel = { active: 'Active', paused: 'Paused', not_connected: 'Not Connected' }[ch.status];
  const btnLabel    = { active: 'Configure', paused: 'Resume', not_connected: 'Connect' }[ch.status];
  const btnClass    = ch.status === 'not_connected' ? 'btn btn-primary' : 'btn';

  return (
    <div className="mkt-channel-card" style={{ borderLeftColor: borderColor }}>
      <div className="mkt-channel-header">
        <div className="mkt-channel-name-row">
          <Icon size={18} style={{ color: borderColor }} />
          <span style={{ fontWeight: 600, color: '#f1f5f9', fontSize: '0.9rem' }}>{ch.name}</span>
          <span className={`mkt-status-dot mkt-dot-${ch.status}`} />
          <span className="text-sm text-muted">{statusLabel}</span>
        </div>
        <TrendBadge pct={ch.trend_pct} />
      </div>

      <div className="mkt-channel-metrics">
        {metrics.map((m, i) => (
          <div key={i}>
            <div className="mkt-channel-metric-label">{m.label}</div>
            <div className="mkt-channel-metric-value mono">{m.value}</div>
          </div>
        ))}
      </div>

      {ch.top_content && (
        <div className="mkt-top-content">Top: {ch.top_content}</div>
      )}
      {ch.notes && (
        <p className="text-sm text-muted" style={{ marginBottom: 12 }}>{ch.notes}</p>
      )}

      <button className={btnClass} style={{ width: '100%', justifyContent: 'center' }}>
        {btnLabel}
      </button>
    </div>
  );
}

export default function ChannelCards({ channels, loading, error }) {
  if (loading && !channels) return (
    <div className="card flex-row" style={{ justifyContent: 'center', padding: 40 }}>
      <Loader2 size={20} className="spin" style={{ color: '#3b82f6' }} />
      <span className="text-muted">Loading channels…</span>
    </div>
  );
  if (error) return <div className="card" style={{ color: '#f87171' }}>Failed to load channels: {error}</div>;
  if (!channels) return null;

  const activeCount  = channels.filter(c => c.status === 'active').length;
  const totalClicks  = channels.reduce((s, c) => s + (c.monthly_clicks || c.referral_clicks || 0), 0);
  const totalSpend   = channels.reduce((s, c) => s + (c.spend_usd || 0), 0);

  return (
    <>
      {/* Summary row */}
      <div className="grid-3" style={{ marginBottom: 20 }}>
        <div className="mkt-metric-card">
          <div className="mkt-metric-label">Active Channels</div>
          <div className="mkt-metric-value">{activeCount} / {channels.length}</div>
        </div>
        <div className="mkt-metric-card">
          <div className="mkt-metric-label">Total Monthly Clicks</div>
          <div className="mkt-metric-value">{totalClicks.toLocaleString()}</div>
        </div>
        <div className="mkt-metric-card">
          <div className="mkt-metric-label">Total Monthly Spend</div>
          <div className="mkt-metric-value">${totalSpend.toFixed(0)}</div>
        </div>
      </div>

      <div className="grid-2">
        {channels.map(ch => <ChannelCard key={ch.channel_id} ch={ch} />)}
      </div>
    </>
  );
}

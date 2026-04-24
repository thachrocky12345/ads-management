import React, { useState, useMemo } from 'react';
import { CheckCircle2, Zap, Loader2 } from 'lucide-react';

const FILTERS = ['All', 'To Do', 'Quick Wins', 'Done'];

const CATEGORY_LABELS = {
  technical_seo: 'Technical SEO',
  content:       'Content',
  keywords:      'Keywords',
  indexing:      'Indexing',
  social:        'Social',
  paid:          'Paid Ads',
  community:     'Community',
  backlinks:     'Backlinks',
};

export default function ActionPlan({ items, loading, error, onToggle }) {
  const [filter, setFilter] = useState('All');

  const filtered = useMemo(() => {
    if (!items) return [];
    if (filter === 'To Do')      return items.filter(i => i.status === 'todo');
    if (filter === 'Quick Wins') return items.filter(i => i.quick_win && i.status !== 'done');
    if (filter === 'Done')       return items.filter(i => i.status === 'done');
    return items;
  }, [items, filter]);

  const quickWins = useMemo(() =>
    items ? items.filter(i => i.quick_win && i.status !== 'done').slice(0, 4) : [],
    [items]
  );

  const doneCount = items ? items.filter(i => i.status === 'done').length : 0;
  const total     = items ? items.length : 0;
  const pct       = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  if (loading && !items) return (
    <div className="card flex-row" style={{ justifyContent: 'center', padding: 40 }}>
      <Loader2 size={20} className="spin" style={{ color: '#3b82f6' }} />
      <span className="text-muted">Loading action plan…</span>
    </div>
  );
  if (error) return <div className="card" style={{ color: '#f87171' }}>Failed to load action plan: {error}</div>;
  if (!items) return null;

  return (
    <>
      {/* Progress + filters */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="flex-row" style={{ justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
          <h2 style={{ marginBottom: 0 }}>Action Plan</h2>
          <div className="mkt-filter-tabs">
            {FILTERS.map(f => (
              <button key={f} className={`mkt-filter-tab ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
            ))}
          </div>
        </div>
        <div className="mkt-progress-container">
          <div className="mkt-progress-label">
            <span>{doneCount} of {total} completed</span>
            <span>{pct}%</span>
          </div>
          <div className="mkt-progress-bar-bg">
            <div className="mkt-progress-bar-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>

      {/* Quick wins section */}
      {filter === 'All' && quickWins.length > 0 && (
        <div className="card" style={{ marginBottom: 20, borderColor: 'rgba(34,197,94,0.25)' }}>
          <div className="flex-row" style={{ marginBottom: 12 }}>
            <Zap size={16} style={{ color: '#4ade80' }} />
            <h2 style={{ marginBottom: 0, color: '#4ade80' }}>Quick Wins</h2>
            <span className="text-sm text-muted">High impact, easy effort — do these first</span>
          </div>
          {quickWins.map(item => <ActionItem key={item.id} item={item} onToggle={onToggle} />)}
        </div>
      )}

      {/* Full list */}
      <div className="card">
        {filter !== 'All' && <h2 style={{ marginBottom: 16 }}>{filter}</h2>}
        {filtered.length === 0
          ? <p className="text-muted text-sm">No items in this category.</p>
          : filtered.map(item => <ActionItem key={item.id} item={item} onToggle={onToggle} />)
        }
      </div>
    </>
  );
}

function ActionItem({ item, onToggle }) {
  const isDone = item.status === 'done';
  const priorityClass = item.priority <= 5 ? 'mkt-priority-high' : item.priority <= 10 ? 'mkt-priority-mid' : 'mkt-priority-low';

  return (
    <div className={`mkt-action-item ${isDone ? 'done' : ''}`}>
      <span className={`mkt-priority-badge ${priorityClass}`}>{item.priority}</span>
      <div
        className={`mkt-checkbox ${isDone ? 'checked' : ''}`}
        onClick={() => onToggle(item.id)}
        role="checkbox"
        aria-checked={isDone}
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && onToggle(item.id)}
      >
        {isDone && <CheckCircle2 size={12} style={{ color: '#fff' }} />}
      </div>
      <div style={{ flex: 1 }}>
        <div className={`mkt-action-title ${isDone ? 'done' : ''}`}>
          {item.title}
          {item.quick_win && !isDone && (
            <span className="mkt-quick-win-badge" style={{ marginLeft: 8 }}>
              <Zap size={10} /> Quick Win
            </span>
          )}
        </div>
        <p className="text-sm text-muted" style={{ marginBottom: 8 }}>{item.description}</p>
        <div className="flex-row flex-wrap gap-sm">
          <span className={`mkt-impact-badge mkt-impact-${item.estimated_impact}`}>
            {item.estimated_impact} impact
          </span>
          <span className={`mkt-effort-badge mkt-effort-${item.estimated_effort}`}>
            {item.estimated_effort}
          </span>
          <span className="text-sm text-muted">{item.time_to_results}</span>
          <span className="text-sm text-muted">
            {CATEGORY_LABELS[item.category] || item.category}
          </span>
          {item.tools.map(tool => (
            <span key={tool} className="mkt-tool-chip">{tool}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

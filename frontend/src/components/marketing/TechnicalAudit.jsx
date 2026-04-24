import React, { useMemo } from 'react';
import { AlertTriangle, Info, Loader2 } from 'lucide-react';

const SEVERITY_ORDER = ['critical', 'warning', 'info'];

const SEVERITY_META = {
  critical: { label: 'Critical', colorClass: 'mkt-severity-critical', icon: AlertTriangle },
  warning:  { label: 'Warning',  colorClass: 'mkt-severity-warning',  icon: AlertTriangle },
  info:     { label: 'Info',     colorClass: 'mkt-severity-info',     icon: Info },
};

export default function TechnicalAudit({ data, loading, error }) {
  const grouped = useMemo(() => {
    if (!data) return {};
    return data.issues.reduce((acc, issue) => {
      acc[issue.severity] = [...(acc[issue.severity] || []), issue];
      return acc;
    }, {});
  }, [data]);

  if (loading) return (
    <div className="card flex-row" style={{ justifyContent: 'center', padding: 40 }}>
      <Loader2 size={20} className="spin" style={{ color: '#3b82f6' }} />
      <span className="text-muted">Running audit…</span>
    </div>
  );
  if (error) return <div className="card" style={{ color: '#f87171' }}>Audit failed: {error}</div>;
  if (!data) return null;

  const criticalCount = (grouped.critical || []).length;
  const warningCount  = (grouped.warning  || []).length;

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div className="flex-row" style={{ justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <div>
          <h2 style={{ marginBottom: 2 }}>Technical Audit</h2>
          <p className="text-sm text-muted">{data.crawled_pages} pages crawled · {data.crawl_date}</p>
        </div>
        <div className="flex-row gap-sm">
          {criticalCount > 0 && (
            <span className="status-badge partial_unsafe">{criticalCount} Critical</span>
          )}
          {warningCount > 0 && (
            <span className="status-badge partial_safe">{warningCount} Warnings</span>
          )}
          <span className="status-badge pending">Score {data.score}/100</span>
        </div>
      </div>

      {SEVERITY_ORDER.map(sev => {
        const issues = grouped[sev];
        if (!issues || issues.length === 0) return null;
        const meta = SEVERITY_META[sev];
        const Icon = meta.icon;
        return (
          <div className="mkt-severity-section" key={sev}>
            <div className="mkt-severity-header">
              <Icon size={15} className={meta.colorClass} />
              <span className={meta.colorClass}>{meta.label}</span>
              <span className="text-muted text-sm">({issues.length})</span>
            </div>
            {issues.map((issue, i) => (
              <div className="mkt-issue-row" key={i}>
                <Icon size={14} className={meta.colorClass} style={{ marginTop: 3, flexShrink: 0 }} />
                <div className="mkt-issue-body">
                  <div className="mkt-issue-title">{issue.title}</div>
                  <div className="mkt-issue-desc">{issue.description}</div>
                  <div className="mkt-issue-meta">
                    {issue.pages_affected > 0 && (
                      <span className="text-sm text-muted">{issue.pages_affected} pages</span>
                    )}
                    <span className={`mkt-effort-badge mkt-effort-${issue.fix_effort}`}>
                      {issue.fix_effort}
                    </span>
                    <span className={`mkt-impact-badge mkt-impact-${issue.impact}`}>
                      {issue.impact} impact
                    </span>
                    <span className="text-sm text-muted" style={{ fontStyle: 'italic' }}>
                      {issue.tool_hint}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

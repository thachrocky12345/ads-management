const BASE = '/api';

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export function fetchAgents() {
  return request('/agents');
}

export function runPipeline(goal, complexity) {
  return request('/pipeline/run', {
    method: 'POST',
    body: JSON.stringify({ goal, complexity }),
  });
}

export function dryRunPipeline(complexity) {
  return request('/pipeline/dry-run', {
    method: 'POST',
    body: JSON.stringify({ complexity }),
  });
}

export function fetchPipelineStatus(runId) {
  return request(`/pipeline/status/${runId}`);
}

// ── Marketing Hub ──────────────────────────────────────────

export function fetchSEOOverview() {
  return request('/marketing/seo/overview');
}

export function fetchSEOKeywords() {
  return request('/marketing/seo/keywords');
}

export function fetchSEOAudit() {
  return request('/marketing/seo/audit');
}

export function fetchChannels() {
  return request('/marketing/channels');
}

export function fetchActionPlan() {
  return request('/marketing/action-plan');
}

export function fetchBudget(monthlyBudget = 300) {
  return request(`/marketing/budget?monthly_budget=${monthlyBudget}`);
}

export function toggleActionItem(itemId) {
  return request(`/marketing/action-plan/${itemId}/toggle`, { method: 'POST' });
}

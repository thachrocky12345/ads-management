import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, Search, Globe, Target, DollarSign } from 'lucide-react';
import SEOOverview from './marketing/SEOOverview.jsx';
import KeywordsPanel from './marketing/KeywordsPanel.jsx';
import TechnicalAudit from './marketing/TechnicalAudit.jsx';
import ChannelCards from './marketing/ChannelCards.jsx';
import ActionPlan from './marketing/ActionPlan.jsx';
import BudgetPlanner from './marketing/BudgetPlanner.jsx';
import {
  fetchSEOOverview, fetchSEOKeywords, fetchSEOAudit,
  fetchChannels, fetchActionPlan, fetchBudget, toggleActionItem,
} from '../api/client.js';

const SUB_TABS = [
  { id: 'overview',  label: 'Overview',       icon: TrendingUp },
  { id: 'seo',       label: 'SEO & Keywords', icon: Search },
  { id: 'channels',  label: 'Channels',       icon: Globe },
  { id: 'actions',   label: 'Action Plan',    icon: Target },
  { id: 'budget',    label: 'Budget Planner', icon: DollarSign },
];

export default function MarketingHub() {
  const [activeTab, setActiveTab] = useState('overview');
  const [loaded, setLoaded]       = useState({});
  const [loading, setLoading]     = useState({});
  const [errors, setErrors]       = useState({});

  const [seoOverview, setSeoOverview]   = useState(null);
  const [keywords, setKeywords]         = useState(null);
  const [audit, setAudit]               = useState(null);
  const [channels, setChannels]         = useState(null);
  const [actionPlan, setActionPlan]     = useState(null);
  const [budget, setBudget]             = useState(null);
  const [monthlyBudget, setMonthlyBudget] = useState(300);

  const setTabLoading = (tab, v) => setLoading(p => ({ ...p, [tab]: v }));
  const setTabError   = (tab, v) => setErrors(p  => ({ ...p, [tab]: v }));
  const markLoaded    = (tab)    => setLoaded(p  => ({ ...p, [tab]: true }));

  const loadOverview = useCallback(async () => {
    if (loaded.overview) return;
    setTabLoading('overview', true);
    try {
      const d = await fetchSEOOverview();
      setSeoOverview(d);
      markLoaded('overview');
    } catch (e) { setTabError('overview', e.message); }
    finally     { setTabLoading('overview', false); }
  }, [loaded.overview]);

  const loadChannels = useCallback(async () => {
    if (loaded.channels) return;
    setTabLoading('channels', true);
    try {
      const d = await fetchChannels();
      setChannels(d);
      markLoaded('channels');
    } catch (e) { setTabError('channels', e.message); }
    finally     { setTabLoading('channels', false); }
  }, [loaded.channels]);

  const loadSEO = useCallback(async () => {
    if (loaded.seo) return;
    setTabLoading('seo', true);
    try {
      const [kw, aud] = await Promise.all([fetchSEOKeywords(), fetchSEOAudit()]);
      setKeywords(kw);
      setAudit(aud);
      markLoaded('seo');
    } catch (e) { setTabError('seo', e.message); }
    finally     { setTabLoading('seo', false); }
  }, [loaded.seo]);

  const loadActions = useCallback(async () => {
    if (loaded.actions) return;
    setTabLoading('actions', true);
    try {
      const d = await fetchActionPlan();
      setActionPlan(d);
      markLoaded('actions');
    } catch (e) { setTabError('actions', e.message); }
    finally     { setTabLoading('actions', false); }
  }, [loaded.actions]);

  const loadBudget = useCallback(async (amount) => {
    setTabLoading('budget', true);
    try {
      const d = await fetchBudget(amount);
      setBudget(d);
      markLoaded('budget');
    } catch (e) { setTabError('budget', e.message); }
    finally     { setTabLoading('budget', false); }
  }, []);

  // Load overview + channels on mount
  useEffect(() => {
    loadOverview();
    loadChannels();
  }, []);

  // Lazy load per tab
  useEffect(() => {
    if (activeTab === 'seo')      loadSEO();
    if (activeTab === 'channels') loadChannels();
    if (activeTab === 'actions')  loadActions();
    if (activeTab === 'budget' && !loaded.budget)  loadBudget(monthlyBudget);
  }, [activeTab]);

  const handleToggleAction = async (itemId) => {
    try {
      const updated = await toggleActionItem(itemId);
      setActionPlan(prev => prev ? prev.map(i => i.id === itemId ? updated : i) : prev);
    } catch (e) { console.error('Toggle failed:', e); }
  };

  const handleBudgetChange = (amount) => {
    setMonthlyBudget(amount);
    loadBudget(amount);
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <>
            <SEOOverview data={seoOverview} loading={loading.overview} error={errors.overview} />
            {channels && (
              <div style={{ marginTop: 20 }}>
                <ChannelCards channels={channels} loading={false} error={null} />
              </div>
            )}
          </>
        );
      case 'seo':
        return (
          <>
            <TechnicalAudit data={audit}    loading={loading.seo} error={errors.seo} />
            <KeywordsPanel  data={keywords} loading={loading.seo} />
          </>
        );
      case 'channels':
        return <ChannelCards channels={channels} loading={loading.channels} error={errors.channels} />;
      case 'actions':
        return (
          <ActionPlan
            items={actionPlan}
            loading={loading.actions}
            error={errors.actions}
            onToggle={handleToggleAction}
          />
        );
      case 'budget':
        return (
          <BudgetPlanner
            plan={budget}
            monthlyBudget={monthlyBudget}
            onBudgetChange={handleBudgetChange}
            loading={loading.budget}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div>
      {/* Header card */}
      <div className="card" style={{ marginBottom: 0, borderRadius: '12px 12px 0 0', borderBottom: 'none' }}>
        <div className="flex-row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <h2 style={{ marginBottom: 2 }}>Marketing Intelligence Hub</h2>
            <p className="text-sm text-muted">AskLongevity.ai — Growth Dashboard</p>
          </div>
          <div className="flex-row gap-sm">
            <div className="hub-live-indicator" />
            <span className="text-sm text-muted">Live Data</span>
          </div>
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="mkt-subtabs">
        {SUB_TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`mkt-subtab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mkt-content">
        {renderTab()}
      </div>
    </div>
  );
}

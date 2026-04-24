import React, { useState } from 'react';
import Dashboard from './components/Dashboard.jsx';
import AgentNetwork from './components/AgentNetwork.jsx';
import CostEstimator from './components/CostEstimator.jsx';
import MarketingHub from './components/MarketingHub.jsx';
import { LayoutDashboard, Network, Calculator, TrendingUp } from 'lucide-react';

const TABS = [
  { id: 'dashboard', label: 'Dashboard',    icon: LayoutDashboard },
  { id: 'network',   label: 'Agent Network', icon: Network },
  { id: 'estimator', label: 'Cost Estimator', icon: Calculator },
  { id: 'marketing', label: 'Marketing Hub', icon: TrendingUp },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'network':
        return <AgentNetwork />;
      case 'estimator':
        return <CostEstimator />;
      case 'marketing':
        return <MarketingHub />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Ads Agent Network</h1>
        <p className="app-subtitle">Multi-Agent AI Campaign Management</p>
      </header>
      <nav className="tabs">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={18} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
      <main className="tab-content">{renderTab()}</main>
    </div>
  );
}

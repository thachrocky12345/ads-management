import React, { useState } from 'react';

const LAYER_COLORS = {
  command: '#8b5cf6',
  intelligence: '#3b82f6',
  platform: '#10b981',
  output: '#f59e0b',
};

const AGENTS = [
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    model: 'Claude Sonnet 4.5',
    budget: 32000,
    layer: 'command',
    description:
      'Central coordinator that decomposes campaign goals into sub-tasks, delegates work to specialist agents, manages inter-agent communication, and assembles final deliverables.',
  },
  {
    id: 'audience_intel',
    name: 'Audience Intel',
    model: 'Claude Sonnet 4.5',
    budget: 16000,
    layer: 'intelligence',
    description:
      'Researches and segments target audiences, analyzes demographics, interests, and behavioral patterns to build detailed audience profiles for each advertising platform.',
  },
  {
    id: 'analytics',
    name: 'Analytics',
    model: 'GPT-5',
    budget: 16000,
    layer: 'intelligence',
    description:
      'Processes campaign performance data, computes KPIs (CPA, ROAS, CTR), identifies trends, and provides optimization recommendations based on historical and real-time metrics.',
  },
  {
    id: 'meta_ads',
    name: 'Meta Ads',
    model: 'GPT-5',
    budget: 12000,
    layer: 'platform',
    description:
      'Manages Facebook and Instagram advertising campaigns including ad set configuration, audience targeting, bid strategies, and creative placement optimization.',
  },
  {
    id: 'google_ads',
    name: 'Google Ads',
    model: 'GPT-5',
    budget: 12000,
    layer: 'platform',
    description:
      'Handles Google Search, Display, and YouTube campaigns. Manages keyword strategies, responsive search ads, bidding, and conversion tracking configuration.',
  },
  {
    id: 'linkedin_ads',
    name: 'LinkedIn Ads',
    model: 'GPT-5',
    budget: 12000,
    layer: 'platform',
    description:
      'Specializes in LinkedIn Campaign Manager operations including B2B targeting by job title, company, industry, and InMail/sponsored content strategies.',
  },
  {
    id: 'creative',
    name: 'Creative',
    model: 'Gemini 3 Pro',
    budget: 24000,
    layer: 'platform',
    description:
      'Generates ad copy, headlines, descriptions, and creative briefs for all platforms. Adapts messaging to each channel\'s best practices and character limits.',
  },
  {
    id: 'reporting',
    name: 'Reporting',
    model: 'Claude Haiku 4.5',
    budget: 8000,
    layer: 'output',
    description:
      'Compiles agent outputs into structured reports, executive summaries, and actionable campaign plans. Produces formatted deliverables for stakeholders.',
  },
];

const LAYERS = [
  { id: 'command', label: 'Command Layer', agents: ['orchestrator'] },
  { id: 'intelligence', label: 'Intelligence Layer', agents: ['audience_intel', 'analytics'] },
  { id: 'platform', label: 'Platform Layer', agents: ['meta_ads', 'google_ads', 'linkedin_ads', 'creative'] },
  { id: 'output', label: 'Output Layer', agents: ['reporting'] },
];

const EDGES = [
  ['orchestrator', 'audience_intel'],
  ['orchestrator', 'analytics'],
  ['orchestrator', 'meta_ads'],
  ['orchestrator', 'google_ads'],
  ['orchestrator', 'linkedin_ads'],
  ['orchestrator', 'creative'],
  ['audience_intel', 'meta_ads'],
  ['audience_intel', 'google_ads'],
  ['audience_intel', 'linkedin_ads'],
  ['analytics', 'meta_ads'],
  ['analytics', 'google_ads'],
  ['analytics', 'linkedin_ads'],
  ['analytics', 'reporting'],
  ['meta_ads', 'reporting'],
  ['google_ads', 'reporting'],
  ['linkedin_ads', 'reporting'],
  ['creative', 'reporting'],
];

const SVG_W = 900;
const SVG_H = 520;
const NODE_W = 160;
const NODE_H = 70;

function getNodePositions() {
  const positions = {};
  const layerYs = [40, 150, 280, 410];

  LAYERS.forEach((layer, li) => {
    const y = layerYs[li];
    const agents = layer.agents;
    const totalW = agents.length * NODE_W + (agents.length - 1) * 30;
    const startX = (SVG_W - totalW) / 2;
    agents.forEach((id, ai) => {
      positions[id] = {
        x: startX + ai * (NODE_W + 30),
        y,
        cx: startX + ai * (NODE_W + 30) + NODE_W / 2,
        cy: y + NODE_H / 2,
      };
    });
  });

  return positions;
}

export default function AgentNetwork() {
  const [selected, setSelected] = useState(null);
  const positions = getNodePositions();
  const selectedAgent = selected ? AGENTS.find((a) => a.id === selected) : null;

  return (
    <div className="network-container">
      <div className="card">
        <h2>Agent Network Architecture</h2>
        <p className="text-sm text-muted" style={{ marginBottom: 16 }}>
          Click on an agent node to view details. Arrows show data flow between agents.
        </p>

        <div className="network-svg-wrapper">
          <svg
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            width="100%"
            style={{ maxHeight: 540, display: 'block' }}
          >
            <defs>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="6"
                refX="8"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#475569" />
              </marker>
              <marker
                id="arrowhead-active"
                markerWidth="8"
                markerHeight="6"
                refX="8"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#60a5fa" />
              </marker>
            </defs>

            {/* Layer labels */}
            {LAYERS.map((layer, li) => {
              const firstAgent = positions[layer.agents[0]];
              return (
                <text
                  key={layer.id}
                  x={14}
                  y={firstAgent.y + NODE_H / 2 + 5}
                  fill={LAYER_COLORS[layer.id]}
                  fontSize="11"
                  fontWeight="600"
                  opacity="0.7"
                >
                  {layer.label}
                </text>
              );
            })}

            {/* Edges */}
            {EDGES.map(([from, to], i) => {
              const f = positions[from];
              const t = positions[to];

              const isActive = selected === from || selected === to;
              const strokeColor = isActive ? '#60a5fa' : '#334155';
              const strokeWidth = isActive ? 1.8 : 1;
              const markerEnd = isActive
                ? 'url(#arrowhead-active)'
                : 'url(#arrowhead)';

              // Connect bottom-center of source to top-center of target
              const x1 = f.cx;
              const y1 = f.y + NODE_H;
              const x2 = t.cx;
              const y2 = t.y;

              const midY = (y1 + y2) / 2;

              return (
                <path
                  key={i}
                  d={`M${x1},${y1} C${x1},${midY} ${x2},${midY} ${x2},${y2}`}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  markerEnd={markerEnd}
                  opacity={selected && !isActive ? 0.2 : 0.8}
                />
              );
            })}

            {/* Nodes */}
            {AGENTS.map((agent) => {
              const pos = positions[agent.id];
              const color = LAYER_COLORS[agent.layer];
              const isSelected = selected === agent.id;

              return (
                <g
                  key={agent.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelected(isSelected ? null : agent.id)}
                >
                  <rect
                    x={pos.x}
                    y={pos.y}
                    width={NODE_W}
                    height={NODE_H}
                    rx={10}
                    ry={10}
                    fill={isSelected ? color : '#1e293b'}
                    stroke={color}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    opacity={selected && !isSelected ? 0.5 : 1}
                  />
                  <text
                    x={pos.cx}
                    y={pos.y + 28}
                    textAnchor="middle"
                    fill={isSelected ? '#fff' : '#f1f5f9'}
                    fontSize="13"
                    fontWeight="600"
                  >
                    {agent.name}
                  </text>
                  <text
                    x={pos.cx}
                    y={pos.y + 46}
                    textAnchor="middle"
                    fill={isSelected ? 'rgba(255,255,255,0.8)' : '#64748b'}
                    fontSize="10"
                  >
                    {agent.model}
                  </text>
                  <text
                    x={pos.cx}
                    y={pos.y + 60}
                    textAnchor="middle"
                    fill={isSelected ? 'rgba(255,255,255,0.6)' : '#475569'}
                    fontSize="9"
                  >
                    {agent.budget.toLocaleString()} tokens
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Detail Panel */}
      {selectedAgent && (
        <div className="agent-detail-panel">
          <h3 style={{ color: LAYER_COLORS[selectedAgent.layer] }}>
            {selectedAgent.name}
          </h3>
          <p className="text-sm" style={{ color: '#94a3b8', marginBottom: 12 }}>
            {selectedAgent.description}
          </p>
          <div className="detail-row">
            <div className="detail-item">
              <span className="detail-label">Model</span>
              <span className="detail-value">{selectedAgent.model}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Token Budget</span>
              <span className="detail-value mono">{selectedAgent.budget.toLocaleString()}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Layer</span>
              <span className="detail-value" style={{ color: LAYER_COLORS[selectedAgent.layer] }}>
                {LAYERS.find((l) => l.id === selectedAgent.layer)?.label}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Connections</span>
              <span className="detail-value">
                {EDGES.filter(([f, t]) => f === selectedAgent.id || t === selectedAgent.id).length}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

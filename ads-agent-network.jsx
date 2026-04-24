import { useState } from "react";

const agents = [
  {
    id: "orchestrator",
    label: "Orchestrator",
    sublabel: "Campaign Manager Agent",
    color: "#F5A623",
    x: 400,
    y: 60,
    size: 64,
    description: "The central brain. Receives your business goal (e.g. 'get 50 leads this month'), breaks it into tasks, and dispatches to specialist agents. Monitors KPIs and re-routes budgets if targets slip.",
    tools: ["Goal → Task decomposition", "Budget arbitration", "Agent health monitoring", "Human-in-the-loop approval"],
    layer: "command",
  },
  {
    id: "audience",
    label: "Audience Intel",
    sublabel: "Targeting & Segmentation Agent",
    color: "#7C3AED",
    x: 400,
    y: 220,
    size: 56,
    description: "Your most important agent given your pain point. Continuously builds and refines audience segments using first-party data, lookalikes, and behavioral signals. Feeds targeting lists to ALL platform agents.",
    tools: ["CRM / pixel data ingestion", "Lookalike generation", "Segment scoring & ranking", "Cross-platform audience sync"],
    layer: "intelligence",
  },
  {
    id: "analytics",
    label: "Analytics",
    sublabel: "Attribution & Insights Agent",
    color: "#0EA5E9",
    x: 180,
    y: 220,
    size: 52,
    description: "Ingests raw performance data from all platforms, deduplicates conversions, and produces a single source of truth. Surfaces which audience segments and creatives are actually driving revenue — not just clicks.",
    tools: ["Multi-touch attribution", "ROAS by segment", "Anomaly detection", "Weekly digest reports"],
    layer: "intelligence",
  },
  {
    id: "meta",
    label: "Meta Ads",
    sublabel: "FB / Instagram Agent",
    color: "#1877F2",
    x: 120,
    y: 390,
    size: 50,
    description: "Manages all Meta campaigns. Pulls audience segments from the Audience Intel agent, auto-rotates creatives, adjusts bids, and pauses underperforming ad sets. Escalates spend decisions above threshold to Orchestrator.",
    tools: ["Campaign CRUD via Meta API", "Creative A/B rotation", "Budget pacing", "Audience upload & refresh"],
    layer: "platform",
  },
  {
    id: "google",
    label: "Google Ads",
    sublabel: "Search & Display Agent",
    color: "#34A853",
    x: 400,
    y: 410,
    size: 50,
    description: "Manages Search, Display, and Local campaigns. Syncs keyword lists, adjusts smart bidding targets, and adds negative keywords based on search term reports. Coordinates with Analytics agent for conversion data.",
    tools: ["Keyword bid management", "Search term mining", "Smart bidding targets", "Local campaign geo-tuning"],
    layer: "platform",
  },
  {
    id: "linkedin",
    label: "LinkedIn Ads",
    sublabel: "B2B Targeting Agent",
    color: "#0A66C2",
    x: 660,
    y: 390,
    size: 50,
    description: "Handles LinkedIn campaigns targeting local professionals and businesses. Uses company size, job title, and industry filters. Especially useful for B2B-adjacent SMBs (e.g. contractors, professional services).",
    tools: ["Job title / industry targeting", "Lead Gen Form management", "Matched audiences sync", "Frequency capping"],
    layer: "platform",
  },
  {
    id: "creative",
    label: "Creative",
    sublabel: "Content & Copy Agent",
    color: "#EC4899",
    x: 620,
    y: 220,
    size: 52,
    description: "Generates ad copy, headlines, and image prompts tailored to each audience segment. Learns which messaging resonates by reading performance data from the Analytics agent. Outputs ready-to-upload creative briefs.",
    tools: ["Copy generation per segment", "Headline A/B variants", "Image prompt generation", "Platform-specific formatting"],
    layer: "intelligence",
  },
  {
    id: "reporting",
    label: "Reporting",
    sublabel: "Alerts & Dashboard Agent",
    color: "#10B981",
    x: 400,
    y: 560,
    size: 46,
    description: "Sends you weekly plain-English summaries: what worked, what didn't, what to approve next. Sends real-time alerts if ROAS drops below threshold or a campaign overspends. No dashboard-staring required.",
    tools: ["Weekly performance digest", "Spend overage alerts", "Approval request triggers", "Competitor signal summaries"],
    layer: "output",
  },
];

const edges = [
  { from: "orchestrator", to: "audience" },
  { from: "orchestrator", to: "analytics" },
  { from: "orchestrator", to: "creative" },
  { from: "audience", to: "meta" },
  { from: "audience", to: "google" },
  { from: "audience", to: "linkedin" },
  { from: "analytics", to: "audience" },
  { from: "analytics", to: "orchestrator" },
  { from: "creative", to: "meta" },
  { from: "creative", to: "google" },
  { from: "creative", to: "linkedin" },
  { from: "meta", to: "reporting" },
  { from: "google", to: "reporting" },
  { from: "linkedin", to: "reporting" },
  { from: "analytics", to: "reporting" },
];

const layerLabels = [
  { y: 48, label: "COMMAND LAYER", color: "#F5A62366" },
  { y: 208, label: "INTELLIGENCE LAYER", color: "#7C3AED44" },
  { y: 378, label: "PLATFORM LAYER", color: "#1877F244" },
  { y: 548, label: "OUTPUT LAYER", color: "#10B98144" },
];

function getPos(id) {
  const a = agents.find((a) => a.id === id);
  return { x: a.x, y: a.y };
}

export default function AgentNetwork() {
  const [selected, setSelected] = useState("orchestrator");
  const agent = agents.find((a) => a.id === selected);

  return (
    <div
      style={{
        fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
        background: "#080B14",
        minHeight: "100vh",
        color: "#E2E8F0",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "32px 16px",
      }}
    >
      <div style={{ textAlign: "center", marginBottom: 8 }}>
        <div style={{ fontSize: 11, letterSpacing: 4, color: "#7C3AED", textTransform: "uppercase", marginBottom: 6 }}>
          Multi-Agent Architecture
        </div>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: "#F8FAFC", letterSpacing: -1 }}>
          SMB Ads Agent Network
        </h1>
        <p style={{ fontSize: 12, color: "#64748B", marginTop: 6 }}>
          Meta · Google · LinkedIn — Audience-first design
        </p>
      </div>

      {/* SVG Network */}
      <div style={{ position: "relative", width: 800, maxWidth: "100%" }}>
        <svg width="800" height="640" style={{ display: "block", maxWidth: "100%" }}>
          {/* Layer backgrounds */}
          {layerLabels.map((l) => (
            <g key={l.y}>
              <rect x={20} y={l.y} width={760} height={130} rx={12}
                fill={l.color} stroke="none" />
              <text x={36} y={l.y + 18} fontSize={9} fill="#94A3B8" letterSpacing={3}
                fontFamily="IBM Plex Mono, monospace" textAnchor="start">
                {l.label}
              </text>
            </g>
          ))}

          {/* Edges */}
          {edges.map((e) => {
            const f = getPos(e.from);
            const t = getPos(e.to);
            const isActive =
              selected === e.from || selected === e.to;
            return (
              <line
                key={`${e.from}-${e.to}`}
                x1={f.x} y1={f.y} x2={t.x} y2={t.y}
                stroke={isActive ? "#F5A623" : "#1E293B"}
                strokeWidth={isActive ? 2 : 1}
                strokeDasharray={isActive ? "none" : "4,4"}
                opacity={isActive ? 0.9 : 0.5}
              />
            );
          })}

          {/* Nodes */}
          {agents.map((a) => {
            const isSelected = selected === a.id;
            const isConnected = edges.some(
              (e) =>
                (e.from === selected && e.to === a.id) ||
                (e.to === selected && e.from === a.id)
            );
            return (
              <g
                key={a.id}
                onClick={() => setSelected(a.id)}
                style={{ cursor: "pointer" }}
              >
                {/* Glow ring */}
                {(isSelected || isConnected) && (
                  <circle
                    cx={a.x} cy={a.y} r={a.size / 2 + 8}
                    fill="none"
                    stroke={a.color}
                    strokeWidth={isSelected ? 2.5 : 1}
                    opacity={isSelected ? 0.7 : 0.3}
                  />
                )}
                {/* Main circle */}
                <circle
                  cx={a.x} cy={a.y} r={a.size / 2}
                  fill={isSelected ? a.color : "#0F172A"}
                  stroke={a.color}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                  opacity={isSelected ? 1 : 0.85}
                />
                {/* Label */}
                <text
                  x={a.x} y={a.y - 4}
                  textAnchor="middle"
                  fontSize={isSelected ? 11 : 10}
                  fontWeight={700}
                  fill={isSelected ? "#080B14" : "#F1F5F9"}
                  fontFamily="IBM Plex Mono, monospace"
                >
                  {a.label}
                </text>
                <text
                  x={a.x} y={a.y + 9}
                  textAnchor="middle"
                  fontSize={7.5}
                  fill={isSelected ? "#08091499" : "#64748B"}
                  fontFamily="IBM Plex Mono, monospace"
                >
                  Agent
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Detail Panel */}
      {agent && (
        <div
          style={{
            width: 800,
            maxWidth: "100%",
            background: "#0F172A",
            border: `1.5px solid ${agent.color}44`,
            borderRadius: 16,
            padding: "24px 28px",
            marginTop: 8,
            boxShadow: `0 0 40px ${agent.color}18`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div
              style={{
                width: 12, height: 12, borderRadius: "50%",
                background: agent.color, boxShadow: `0 0 8px ${agent.color}`,
                flexShrink: 0,
              }}
            />
            <div>
              <div style={{ fontWeight: 700, fontSize: 16, color: "#F8FAFC" }}>
                {agent.label} Agent
              </div>
              <div style={{ fontSize: 11, color: "#64748B" }}>{agent.sublabel}</div>
            </div>
            <div
              style={{
                marginLeft: "auto",
                fontSize: 9,
                letterSpacing: 2,
                color: agent.color,
                border: `1px solid ${agent.color}55`,
                borderRadius: 4,
                padding: "3px 8px",
                textTransform: "uppercase",
              }}
            >
              {agent.layer}
            </div>
          </div>

          <p style={{ fontSize: 13, color: "#94A3B8", lineHeight: 1.7, margin: "0 0 16px" }}>
            {agent.description}
          </p>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {agent.tools.map((t) => (
              <span
                key={t}
                style={{
                  fontSize: 11,
                  color: agent.color,
                  background: `${agent.color}15`,
                  border: `1px solid ${agent.color}30`,
                  borderRadius: 6,
                  padding: "4px 10px",
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Build order */}
      <div style={{ width: 800, maxWidth: "100%", marginTop: 20 }}>
        <div style={{ fontSize: 10, letterSpacing: 3, color: "#475569", textTransform: "uppercase", marginBottom: 12 }}>
          Recommended Build Order
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {[
            { phase: "Phase 1", title: "Data Foundation", items: ["Analytics Agent", "Audience Intel Agent"], color: "#7C3AED" },
            { phase: "Phase 2", title: "Platform Ops", items: ["Meta Ads Agent", "Google Ads Agent"], color: "#1877F2" },
            { phase: "Phase 3", title: "Expand & Create", items: ["LinkedIn Agent", "Creative Agent"], color: "#EC4899" },
            { phase: "Phase 4", title: "Orchestrate", items: ["Orchestrator Agent", "Reporting Agent"], color: "#F5A623" },
          ].map((p) => (
            <div key={p.phase} style={{
              background: "#0F172A",
              border: `1px solid ${p.color}33`,
              borderRadius: 10,
              padding: "14px 14px",
            }}>
              <div style={{ fontSize: 9, color: p.color, letterSpacing: 2, marginBottom: 4 }}>{p.phase}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#F1F5F9", marginBottom: 8 }}>{p.title}</div>
              {p.items.map((i) => (
                <div key={i} style={{ fontSize: 10, color: "#64748B", marginBottom: 3 }}>→ {i}</div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div style={{ fontSize: 10, color: "#334155", marginTop: 20 }}>
        Click any agent node to explore its role and capabilities
      </div>
    </div>
  );
}

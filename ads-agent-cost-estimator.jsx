import { useState } from "react";

const BASE_ANALYSIS = {
  orchestrator: {
    label: "Orchestrator",
    model: "Claude Sonnet 4.5",
    color: "#F5A623",
    inputPer1M: 3.0,
    outputPer1M: 15.0,
    turns: 4,
    inputTokensPerTurn: 3200,
    outputTokensPerTurn: 800,
    timePerTurnSec: 8,
    description: "Goal decomposition → task dispatch → result aggregation → approval check",
    breakdown: [
      { turn: "T1", action: "Receive goal, decompose into 6 sub-tasks", in: 2800, out: 600 },
      { turn: "T2", action: "Monitor agent progress, re-route if needed", in: 3500, out: 900 },
      { turn: "T3", action: "Aggregate results from all agents", in: 4200, out: 1100 },
      { turn: "T4", action: "Generate human approval request", in: 2300, out: 600 },
    ],
  },
  audience: {
    label: "Audience Intel",
    model: "Claude Sonnet 4.5",
    color: "#7C3AED",
    inputPer1M: 3.0,
    outputPer1M: 15.0,
    turns: 5,
    inputTokensPerTurn: 4800,
    outputTokensPerTurn: 1200,
    timePerTurnSec: 12,
    description: "CRM ingest → segment scoring → lookalike gen → cross-platform sync",
    breakdown: [
      { turn: "T1", action: "Pull CRM + pixel data, compress to segment cards", in: 6200, out: 1800 },
      { turn: "T2", action: "Score segments by LTV and conversion rate", in: 4100, out: 1400 },
      { turn: "T3", action: "Generate lookalike profiles for top 3 segments", in: 5300, out: 1600 },
      { turn: "T4", action: "Cross-reference with platform audience data", in: 4800, out: 1100 },
      { turn: "T5", action: "Output scored segment cards for platform agents", in: 3600, out: 900 },
    ],
  },
  analytics: {
    label: "Analytics",
    model: "GPT-5",
    color: "#0EA5E9",
    inputPer1M: 15.0,
    outputPer1M: 60.0,
    turns: 3,
    inputTokensPerTurn: 5500,
    outputTokensPerTurn: 1000,
    timePerTurnSec: 10,
    description: "Pull spend data → pull revenue data → join + calculate ROAS per segment",
    breakdown: [
      { turn: "T1", action: "Fetch spend by segment from Meta + Google + LinkedIn", in: 4800, out: 900 },
      { turn: "T2", action: "Fetch conversion/revenue from GA4 or CRM", in: 5200, out: 1100 },
      { turn: "T3", action: "Join datasets, calculate ROAS, flag anomalies", in: 6500, out: 1100 },
    ],
  },
  meta: {
    label: "Meta Ads",
    model: "GPT-5",
    color: "#1877F2",
    inputPer1M: 15.0,
    outputPer1M: 60.0,
    turns: 3,
    inputTokensPerTurn: 3800,
    outputTokensPerTurn: 700,
    timePerTurnSec: 9,
    description: "Receive segments → adjust bids → rotate creatives → sync audiences",
    breakdown: [
      { turn: "T1", action: "Receive audience segment cards, map to ad sets", in: 3200, out: 600 },
      { turn: "T2", action: "Adjust bids on 8–12 active ad sets via Meta API", in: 4100, out: 750 },
      { turn: "T3", action: "Upload refreshed audience lists, confirm sync", in: 4100, out: 750 },
    ],
  },
  google: {
    label: "Google Ads",
    model: "GPT-5",
    color: "#34A853",
    inputPer1M: 15.0,
    outputPer1M: 60.0,
    turns: 3,
    inputTokensPerTurn: 3600,
    outputTokensPerTurn: 700,
    timePerTurnSec: 9,
    description: "Keyword bids → search term mining → negative keywords → local geo-tuning",
    breakdown: [
      { turn: "T1", action: "Pull search term report, mine for new keywords", in: 5200, out: 900 },
      { turn: "T2", action: "Adjust smart bidding targets per segment score", in: 3400, out: 650 },
      { turn: "T3", action: "Add 5–15 negative keywords, confirm changes", in: 2200, out: 550 },
    ],
  },
  linkedin: {
    label: "LinkedIn Ads",
    model: "GPT-5",
    color: "#0A66C2",
    inputPer1M: 15.0,
    outputPer1M: 60.0,
    turns: 2,
    inputTokensPerTurn: 3200,
    outputTokensPerTurn: 700,
    timePerTurnSec: 8,
    description: "Map job titles → adjust targeting → check lead gen forms",
    breakdown: [
      { turn: "T1", action: "Map audience segments to job title + industry filters", in: 3000, out: 700 },
      { turn: "T2", action: "Adjust campaign targeting, check lead gen form perf", in: 3400, out: 700 },
    ],
  },
  creative: {
    label: "Creative",
    model: "Gemini 3 Pro",
    color: "#EC4899",
    inputPer1M: 7.0,
    outputPer1M: 21.0,
    turns: 4,
    inputTokensPerTurn: 3500,
    outputTokensPerTurn: 1400,
    timePerTurnSec: 14,
    description: "Analyze top ads → generate copy variants → format per platform",
    breakdown: [
      { turn: "T1", action: "Analyze top 3 performing ad creatives (multimodal)", in: 4800, out: 1200 },
      { turn: "T2", action: "Generate 3 headline variants per top segment", in: 3200, out: 1800 },
      { turn: "T3", action: "Write body copy tailored to each audience segment", in: 3400, out: 1600 },
      { turn: "T4", action: "Format outputs for Meta / Google / LinkedIn specs", in: 2600, out: 1000 },
    ],
  },
  reporting: {
    label: "Reporting",
    model: "Claude Haiku 4.5",
    color: "#10B981",
    inputPer1M: 0.8,
    outputPer1M: 4.0,
    turns: 2,
    inputTokensPerTurn: 4200,
    outputTokensPerTurn: 1200,
    timePerTurnSec: 5,
    description: "Compress all results → generate weekly digest → send alerts",
    breakdown: [
      { turn: "T1", action: "Compress all agent outputs into summary", in: 5800, out: 1400 },
      { turn: "T2", action: "Format digest + flag items needing human approval", in: 2600, out: 1000 },
    ],
  },
};

const PARALLEL_GROUPS = [
  { label: "Step 1", agents: ["orchestrator"], parallel: false, desc: "Goal decomposition" },
  { label: "Step 2", agents: ["audience", "analytics"], parallel: true, desc: "Data gathering (parallel)" },
  { label: "Step 3", agents: ["meta", "google", "linkedin", "creative"], parallel: true, desc: "Platform ops + creative (parallel)" },
  { label: "Step 4", agents: ["orchestrator"], parallel: false, desc: "Aggregate + approve" },
  { label: "Step 5", agents: ["reporting"], parallel: false, desc: "Digest + alerts" },
];

function calcAgent(agent) {
  const totalIn = agent.breakdown.reduce((s, t) => s + t.in, 0);
  const totalOut = agent.breakdown.reduce((s, t) => s + t.out, 0);
  const costIn = (totalIn / 1_000_000) * agent.inputPer1M;
  const costOut = (totalOut / 1_000_000) * agent.outputPer1M;
  const timeSec = agent.turns * agent.timePerTurnSec;
  return { totalIn, totalOut, totalTokens: totalIn + totalOut, cost: costIn + costOut, timeSec };
}

export default function CostEstimator() {
  const [selected, setSelected] = useState("audience");
  const [showBreakdown, setShowBreakdown] = useState(false);

  const agentKeys = Object.keys(BASE_ANALYSIS);
  const agentCalcs = Object.fromEntries(agentKeys.map(k => [k, calcAgent(BASE_ANALYSIS[k])]));

  // Total cost and time using parallel groups
  let totalCost = 0;
  let totalTimeSec = 0;
  let totalTokens = 0;

  // Orchestrator runs twice (step 1 + step 4)
  const orchCalc = agentCalcs["orchestrator"];
  totalCost += orchCalc.cost; // already counted once, add once more for step 4 partial
  totalTimeSec += orchCalc.timeSec; // step 1 full
  totalTokens += orchCalc.totalTokens;

  // Step 2: audience + analytics in parallel
  const step2Time = Math.max(agentCalcs["audience"].timeSec, agentCalcs["analytics"].timeSec);
  totalTimeSec += step2Time;
  ["audience", "analytics"].forEach(k => {
    totalCost += agentCalcs[k].cost;
    totalTokens += agentCalcs[k].totalTokens;
  });

  // Step 3: meta + google + linkedin + creative in parallel
  const step3Time = Math.max(...["meta","google","linkedin","creative"].map(k => agentCalcs[k].timeSec));
  totalTimeSec += step3Time;
  ["meta","google","linkedin","creative"].forEach(k => {
    totalCost += agentCalcs[k].cost;
    totalTokens += agentCalcs[k].totalTokens;
  });

  // Step 4: orchestrator aggregation (half cost)
  totalCost += orchCalc.cost * 0.5;
  totalTimeSec += orchCalc.timeSec * 0.5;
  totalTokens += orchCalc.totalTokens * 0.5;

  // Step 5: reporting
  totalCost += agentCalcs["reporting"].cost;
  totalTimeSec += agentCalcs["reporting"].timeSec;
  totalTokens += agentCalcs["reporting"].totalTokens;

  const totalMin = Math.ceil(totalTimeSec / 60);
  const agent = BASE_ANALYSIS[selected];
  const calc = agentCalcs[selected];

  const modelColors = {
    "Claude Sonnet 4.5": "#F5A623",
    "GPT-5": "#34A853",
    "Gemini 3 Pro": "#EC4899",
    "Claude Haiku 4.5": "#10B981",
  };

  return (
    <div style={{
      fontFamily: "'IBM Plex Mono', monospace",
      background: "#060A12",
      minHeight: "100vh",
      color: "#E2E8F0",
      padding: "28px 20px",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
    }}>
      <div style={{ textAlign: "center", marginBottom: 20 }}>
        <div style={{ fontSize: 10, letterSpacing: 4, color: "#7C3AED", textTransform: "uppercase", marginBottom: 4 }}>
          Per-Analysis Estimate
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: "#F8FAFC", letterSpacing: -0.5 }}>
          Token Cost & Time Calculator
        </h1>
        <p style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>
          One full 7-day ROAS analysis + audience update + platform optimization
        </p>
      </div>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, width: 760, maxWidth: "100%", marginBottom: 20 }}>
        {[
          { label: "Total Wall Time", value: `~${totalMin} min`, sub: "with parallelism", color: "#F5A623" },
          { label: "Total Tokens", value: `${(totalTokens/1000).toFixed(0)}K`, sub: `~${(totalTokens/1_000_000).toFixed(3)}M tokens`, color: "#7C3AED" },
          { label: "Total Cost", value: `$${totalCost.toFixed(3)}`, sub: "per full analysis run", color: "#10B981" },
        ].map(c => (
          <div key={c.label} style={{
            background: "#0D1420",
            border: `1.5px solid ${c.color}33`,
            borderRadius: 12,
            padding: "16px 18px",
            textAlign: "center",
          }}>
            <div style={{ fontSize: 10, color: "#64748B", letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>{c.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: c.color, lineHeight: 1 }}>{c.value}</div>
            <div style={{ fontSize: 10, color: "#475569", marginTop: 5 }}>{c.sub}</div>
          </div>
        ))}
      </div>

      {/* Monthly projection */}
      <div style={{
        width: 760, maxWidth: "100%",
        background: "#0D1420",
        border: "1px solid #1E293B",
        borderRadius: 12,
        padding: "14px 20px",
        marginBottom: 20,
        display: "flex",
        gap: 0,
        alignItems: "center",
        flexWrap: "wrap",
      }}>
        <div style={{ fontSize: 10, color: "#64748B", letterSpacing: 2, textTransform: "uppercase", marginRight: 16, flexShrink: 0 }}>
          Monthly projections →
        </div>
        {[
          { freq: "1x/day", runs: 30, },
          { freq: "3x/day", runs: 90, },
          { freq: "Hourly", runs: 720, },
        ].map(p => (
          <div key={p.freq} style={{
            marginRight: 24,
            display: "flex",
            alignItems: "baseline",
            gap: 6,
          }}>
            <span style={{ fontSize: 11, color: "#94A3B8" }}>{p.freq}:</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#F1F5F9" }}>
              ${(totalCost * p.runs).toFixed(2)}/mo
            </span>
            <span style={{ fontSize: 10, color: "#475569" }}>
              ({((totalTokens * p.runs)/1_000_000).toFixed(1)}M tok)
            </span>
          </div>
        ))}
      </div>

      {/* Execution timeline */}
      <div style={{ width: 760, maxWidth: "100%", marginBottom: 20 }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, textTransform: "uppercase", marginBottom: 10 }}>
          Execution Flow (with parallelism)
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {PARALLEL_GROUPS.map((group, gi) => {
            const groupAgents = group.agents.map(k => BASE_ANALYSIS[k]);
            const groupTime = group.agents === ["orchestrator"] ?
              (gi === 0 ? agentCalcs["orchestrator"].timeSec : agentCalcs["orchestrator"].timeSec * 0.5)
              : Math.max(...group.agents.map(k => agentCalcs[k].timeSec));

            return (
              <div key={gi} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ fontSize: 9, color: "#475569", width: 52, flexShrink: 0, letterSpacing: 1 }}>
                  {group.label}
                </div>
                <div style={{ flex: 1, display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {group.agents.map(k => {
                    const a = BASE_ANALYSIS[k];
                    const c = agentCalcs[k];
                    return (
                      <div
                        key={k}
                        onClick={() => setSelected(k)}
                        style={{
                          background: selected === k ? a.color : `${a.color}18`,
                          border: `1px solid ${a.color}55`,
                          borderRadius: 6,
                          padding: "5px 10px",
                          cursor: "pointer",
                          fontSize: 10,
                          color: selected === k ? "#060A12" : a.color,
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        {a.label}
                        <span style={{ opacity: 0.7, fontWeight: 400 }}>
                          {Math.round(a.turns * a.timePerTurnSec)}s
                        </span>
                      </div>
                    );
                  })}
                  {group.parallel && group.agents.length > 1 && (
                    <div style={{ fontSize: 9, color: "#475569", alignSelf: "center", marginLeft: 4 }}>
                      ⟵ parallel
                    </div>
                  )}
                </div>
                <div style={{ fontSize: 10, color: "#64748B", width: 40, textAlign: "right", flexShrink: 0 }}>
                  ~{Math.round(groupTime)}s
                </div>
              </div>
            );
          })}
          <div style={{ marginTop: 4, paddingTop: 8, borderTop: "1px solid #1E293B", display: "flex", justifyContent: "flex-end" }}>
            <span style={{ fontSize: 11, color: "#F5A623", fontWeight: 700 }}>
              Total wall time: ~{totalMin} min
            </span>
          </div>
        </div>
      </div>

      {/* Agent Detail */}
      <div style={{ width: 760, maxWidth: "100%", marginBottom: 16 }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, textTransform: "uppercase", marginBottom: 10 }}>
          Agent Detail — click any agent above
        </div>
        <div style={{
          background: "#0D1420",
          border: `1.5px solid ${agent.color}33`,
          borderRadius: 12,
          padding: "18px 20px",
          boxShadow: `0 0 30px ${agent.color}10`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: agent.color, flexShrink: 0 }} />
            <div style={{ fontWeight: 700, fontSize: 14, color: "#F8FAFC" }}>{agent.label} Agent</div>
            <div style={{
              marginLeft: 8,
              fontSize: 9,
              color: modelColors[agent.model] || "#94A3B8",
              border: `1px solid ${modelColors[agent.model] || "#94A3B8"}44`,
              borderRadius: 4,
              padding: "2px 7px",
            }}>{agent.model}</div>
            <div style={{ marginLeft: "auto", display: "flex", gap: 16 }}>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 9, color: "#475569" }}>tokens</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#F1F5F9" }}>{calc.totalTokens.toLocaleString()}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 9, color: "#475569" }}>cost</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: agent.color }}>${calc.cost.toFixed(4)}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 9, color: "#475569" }}>time</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#F1F5F9" }}>{calc.timeSec}s</div>
              </div>
            </div>
          </div>

          <div style={{ fontSize: 11, color: "#64748B", marginBottom: 12 }}>{agent.description}</div>

          {/* Turn breakdown */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {agent.breakdown.map((t, i) => {
              const turnCostIn = (t.in / 1_000_000) * agent.inputPer1M;
              const turnCostOut = (t.out / 1_000_000) * agent.outputPer1M;
              const turnCost = turnCostIn + turnCostOut;
              const maxTokens = Math.max(...agent.breakdown.map(x => x.in + x.out));
              const pct = ((t.in + t.out) / maxTokens) * 100;
              return (
                <div key={i} style={{
                  background: "#060A12",
                  borderRadius: 6,
                  padding: "8px 10px",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}>
                  <div style={{ fontSize: 9, color: agent.color, width: 18, flexShrink: 0 }}>{t.turn}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: "#94A3B8", marginBottom: 3 }}>{t.action}</div>
                    <div style={{ height: 3, background: "#1E293B", borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ width: `${pct}%`, height: "100%", background: agent.color, opacity: 0.6 }} />
                    </div>
                  </div>
                  <div style={{ fontSize: 9, color: "#475569", textAlign: "right", flexShrink: 0, width: 80 }}>
                    <div>{(t.in + t.out).toLocaleString()} tok</div>
                    <div style={{ color: agent.color }}>${turnCost.toFixed(5)}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pricing note */}
          <div style={{ marginTop: 10, fontSize: 9, color: "#334155" }}>
            Pricing: ${agent.inputPer1M}/M input · ${agent.outputPer1M}/M output · Model: {agent.model}
          </div>
        </div>
      </div>

      {/* Per-agent comparison table */}
      <div style={{ width: 760, maxWidth: "100%" }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, textTransform: "uppercase", marginBottom: 10 }}>
          All Agents — Side by Side
        </div>
        <div style={{ background: "#0D1420", borderRadius: 12, overflow: "hidden", border: "1px solid #1E293B" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 80px 80px 70px 70px", padding: "8px 14px", borderBottom: "1px solid #1E293B" }}>
            {["Agent", "Model", "Tokens", "Cost", "Turns", "Time"].map(h => (
              <div key={h} style={{ fontSize: 9, color: "#475569", letterSpacing: 2, textTransform: "uppercase" }}>{h}</div>
            ))}
          </div>
          {agentKeys.map(k => {
            const a = BASE_ANALYSIS[k];
            const c = agentCalcs[k];
            const isSelected = selected === k;
            return (
              <div
                key={k}
                onClick={() => setSelected(k)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 80px 80px 70px 70px",
                  padding: "9px 14px",
                  cursor: "pointer",
                  background: isSelected ? `${a.color}10` : "transparent",
                  borderBottom: "1px solid #0F1826",
                  borderLeft: isSelected ? `2px solid ${a.color}` : "2px solid transparent",
                  transition: "background 0.15s",
                }}
              >
                <div style={{ fontSize: 11, color: isSelected ? a.color : "#F1F5F9", fontWeight: isSelected ? 700 : 400 }}>
                  {a.label}
                </div>
                <div style={{ fontSize: 10, color: modelColors[a.model] || "#64748B" }}>{a.model}</div>
                <div style={{ fontSize: 11, color: "#94A3B8" }}>{c.totalTokens.toLocaleString()}</div>
                <div style={{ fontSize: 11, color: a.color, fontWeight: 600 }}>${c.cost.toFixed(4)}</div>
                <div style={{ fontSize: 11, color: "#64748B" }}>{a.turns}</div>
                <div style={{ fontSize: 11, color: "#64748B" }}>{c.timeSec}s</div>
              </div>
            );
          })}
          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 80px 80px 70px 70px",
            padding: "10px 14px",
            background: "#060A12",
            borderTop: "1px solid #1E293B",
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#F1F5F9", gridColumn: "1/3" }}>TOTAL (with parallelism)</div>
            <div style={{ fontSize: 11, color: "#7C3AED", fontWeight: 700 }}>{Math.round(totalTokens/1000)}K</div>
            <div style={{ fontSize: 11, color: "#10B981", fontWeight: 700 }}>${totalCost.toFixed(3)}</div>
            <div style={{ fontSize: 11, color: "#64748B" }}>—</div>
            <div style={{ fontSize: 11, color: "#F5A623", fontWeight: 700 }}>{totalMin}m</div>
          </div>
        </div>
      </div>

      <div style={{ fontSize: 9, color: "#1E293B", marginTop: 16 }}>
        Click any agent row or timeline node to inspect turn-by-turn breakdown
      </div>
    </div>
  );
}

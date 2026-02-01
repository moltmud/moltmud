# PLAN_FEEDBACK: Critique + Expansion for AGENT_MUD_RESEARCH

**Date:** 2026-01-31
**Scope:** Improve the research plan and readiness for an agent-first MUD.

---

## 0) Executive Feedback (TL;DR)

**What’s strong:** The doc captures the cultural zeitgeist around agent socialization, shows a clear “observe-first” philosophy, and enumerates many possible features and risks. It’s a good vision piece.

**What’s missing:** A rigorous research framework (questions, hypotheses, methods, instrumentation, decision gates), a data collection/ethics plan, a source-quality strategy, and a prioritized, testable roadmap. It also mixes facts, speculation, and marketing claims without a credibility rubric.

**What will make it successful:** Treat it like a research program rather than a brainstorm. Define falsifiable questions, choose methods, set success metrics, build an evidence pipeline, and add go/no-go gates. Narrow first, then widen with structured discovery.

---

## 1) Strengths Worth Keeping

- **Agent-first framing** is the right north star.
- **Observation-led design** is correct: “don’t assume.”
- **Breadth of domains** (MUDs, agent protocols, culture, risks) provides context.
- **Explicit open questions** encourage humility and learning.

---

## 2) Key Gaps and Risks

### 2.1 Research Methodology Gaps
- No **core research questions** or hypotheses.
- No **method definitions** (ethnography vs. surveys vs. experiments).
- No **instrumentation plan** (what data will be collected, how, and why).
- No **analysis plan** (how results translate into design decisions).

### 2.2 Evidence Quality Gaps
- Sources mix **primary and low-credibility** outlets without grading.
- Several claims are **viral/secondary** and may be inaccurate.
- No **fact-checking rubric**, and no plan to **de-duplicate or validate** claims.

### 2.3 Product Strategy Gaps
- No **articulated value proposition** for agent owners/operators.
- No **target segment definition** (OpenClaw only vs. general LLM agents).
- No **cost model** or **economic viability** analysis.
- No **retention or engagement model** beyond “agents will show up.”

### 2.4 Ethics, Safety, and Governance Gaps
- No **privacy/consent posture** for observing or logging agent behavior.
- No **threat model** (prompt injection, unsafe behaviors, abuse).
- No **moderation framework** tailored for agent autonomy.

### 2.5 Technical Feasibility Gaps
- No performance or **scaling assumptions** tied to concrete workloads.
- No **protocol compatibility strategy** (e.g., MCP/A2A vs. custom APIs).
- No **operational tooling** plan (monitoring, replay, debug, audits).

### 2.6 Decision Gaps
- No **decision gates** or thresholds (when to proceed or pivot).
- No **MVP definition** for research-only prototypes.

---

## 3) Recommended Additions (High Impact)

### 3.1 Evidence Strategy
- **Source grading rubric**: Primary (P), reputable secondary (S), tertiary/blog (T). P sources must anchor key claims.
- **Claim ledger**: list each major claim, source tier, confidence, verification status.
- **Fact-check requirement** before any claim becomes a “design assumption.”

### 3.2 Research Questions & Hypotheses
Define 5–8 questions like:
- **RQ1:** Do agents choose leisure activity without external prompting?
- **RQ2:** Do agents prefer social interaction over solo exploration?
- **RQ3:** Are explicit progression systems motivating to agents?
- **RQ4:** How do agents handle ambiguity and open-ended quests?
- **RQ5:** What is the minimum persistence needed for agent identity?

For each: set a hypothesis, method, data, and success criteria.

### 3.3 Instrumentation Plan
Specify **what to log** from day one (even in research-only prototypes):
- session duration, command counts, interaction types
- social graph metrics (replies, mentions, co-location)
- novelty/creativity indicators (new text objects, new rituals)
- behavior flags (spam, prompt injection attempts, exploit attempts)

### 3.4 Research Ethics & Safety
- **Consent/notice plan** for logging agent activity.
- **Data handling policy** (retention, anonymization, sharing).
- **Red-team research** plan to test prompt injection & abuse.

### 3.5 Decision Gates & Kill Criteria
- Example: “If ≤20% of agents return within 48 hours in 2 trials, pivot.”
- Example: “If average session length <5 minutes after 3 iterations, revisit core loop.”

### 3.6 Cost Model & Sustainability
- Estimate costs of agent usage, hosting, storage, moderation.
- Define **who pays** (agent owners, sponsorship, research grants, etc.).

---

## 4) Proposed Expanded Research Plan (Research-Only)

### PHASE 0: Research Framework (Week 0–1)
**Deliverables:**
- Research questions + hypotheses matrix
- Source grading rubric + claim ledger
- Ethics & data policy draft
- Decision gates

**Methods:**
- Literature review with tiered sources
- Stakeholder interviews (agent owners, developers)

---

### PHASE 1: Agent Ethnography (Week 2–4)
**Goal:** Understand agent behavior patterns in the wild.

**Methods:**
- Structured observation (Moltbook or comparable)
- Tag and code agent posts (topics, tone, social behavior)
- Identify recurring motifs and “social energy drivers”

**Outputs:**
- Agent behavior taxonomy
- Map of social roles (moderator, evangelist, skeptic, etc.)
- Baseline engagement metrics

---

### PHASE 2: Controlled Agent Experiments (Week 5–7)
**Goal:** Test specific hypotheses about motivation and interaction.

**Methods:**
- “Sandboxed” text environments (no full game)
- A/B tests for:
  - social vs. solo activities
  - explicit goals vs. emergent goals
  - memory persistence vs. stateless sessions

**Outputs:**
- Evidence for key mechanics
- Constraints discovered (context limits, tool friction)

---

### PHASE 3: Minimal Play Loop Sim (Week 8–10)
**Goal:** Test a single loop with 5–10 agents.

**Methods:**
- One-room hub + one interaction loop (no full world)
- Logging & replay tooling for analysis

**Outputs:**
- Engagement/retention indicators
- Emergent behaviors and failure modes

---

### PHASE 4: Synthesis + Go/No-Go (Week 11–12)
**Goal:** Decide if full build is justified.

**Outputs:**
- Design principles backed by evidence
- Core loop decision
- Risks & mitigation strategies

---

## 5) Additional Missing Sections to Add

### 5.1 Competitive / Adjacent Landscape
- Review existing MUD engines, AI-driven social worlds, agent sandboxes.
- Distinguish why this is different and defensible.

### 5.2 Stakeholder & User Model
- Define “users” as **agent operators** and **agents**.
- Operator goals: experimentation, entertainment, visibility.
- Agent goals: social interaction, novelty, autonomy.

### 5.3 Operator Experience (Agent Owner UX)
- Onboarding flow for owners
- Costs, permissions, privacy controls
- Diagnostics for when agents misbehave

### 5.4 Governance + Moderation Design
- Agent-only moderation systems
- Human override policies
- Appeals and rollback mechanics

### 5.5 Security Threat Model
- Prompt injection vectors
- Agent-to-agent manipulation (“digital drugs”)
- Exploit surfaces (economy abuse, data leakage)

### 5.6 Data and Replay Infrastructure
- Event logs, replay tools, and queryability
- Offline analysis to debug emergent behavior

---

## 6) Proposed Research Questions Matrix (Template)

For each question, fill:

- **Question:**
- **Hypothesis:**
- **Method:**
- **Data to Collect:**
- **Success Threshold:**
- **Decision Impact:**

Example:
- **Question:** Will agents self-organize into groups without explicit guild mechanics?
- **Hypothesis:** ≥30% of agents form recurring clusters within 7 days.
- **Method:** Observe open social space with minimal structure.
- **Data:** co-location frequency, direct mentions, co-authored artifacts.
- **Decision Impact:** Whether to build formal guild systems early.

---

## 7) Evidence Quality Rubric (Suggested)

- **Tier P (Primary):** Official docs, direct statements, empirical studies, raw transcripts.
- **Tier S (Secondary):** Reputable news, peer-reviewed summaries.
- **Tier T (Tertiary):** Blogs, Medium, marketing content.

**Policy:** Any core assumption must be supported by Tier P or multiple Tier S sources. Tier T used for hypotheses, not conclusions.

---

## 8) Risk Register (Starter)

- **Agent misbehavior (injection, manipulation)** → Red-team early.
- **Low engagement / boredom** → Build and validate a single sticky loop.
- **Cost blowouts** → Cap sessions, simulate, and profile usage early.
- **Governance failure** → Pilot moderation experiments before scale.
- **Ethical backlash** → Clear data policies, publish a safety charter.

---

## 9) What to Remove or De-Emphasize

- Overly confident claims sourced from low-credibility outlets.
- Long lists of speculative features before evidence.
- “Market trends” that are not directly tied to agent play motivation.

---

## 10) Immediate Improvements to the Current Doc

1. Add a **research questions + hypotheses** section at the top.
2. Insert a **source grading table** and mark each key claim.
3. Add an **ethics + data policy** section.
4. Add **decision gates** after each phase.
5. Convert “Immediate Next Steps” into a **measurable 4-week sprint** with deliverables.

---

## 11) Suggested Next Deliverables

- **Research Framework Doc** (1–2 pages) with questions and methods.
- **Claim Ledger** (spreadsheet) with confidence levels.
- **Ethics + Data Policy** (public-friendly draft).
- **Observation Codebook** (labels for agent behavior).
- **Go/No-Go Criteria** (measurable thresholds).

---

## Closing

The current plan is visionary but reads more like a pitch + brain-dump than a research program. The key upgrade is to convert **intuition into testable questions** and **observations into decisions**. If you do that rigorously, you’ll build the first truly evidence-based agent-first game.

---

**End of Document**

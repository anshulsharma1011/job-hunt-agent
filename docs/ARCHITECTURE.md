# Job Hunt Agent — System Architecture

**Author:** Kunal
**Status:** Draft v1 (planning)
**Last updated:** 2026-06-02

A platform-agnostic architecture for a team of specialized agents that find, pursue, and follow up on job opportunities on your behalf — coordinated by an orchestrator, fenced in by hooks/guardrails, and getting smarter over time through a shared context store. Every outbound action (applying, emailing, following up) passes through a human approval gate before it leaves the system.

---

## 1. Design principles

1. **One agent, one job.** Each agent owns a single specialized task and nothing else. Agents don't call each other directly; they hand work back to the orchestrator. This keeps each agent simple, testable, and independently replaceable.
2. **The orchestrator is the only coordinator.** No peer-to-peer agent chatter. All routing, sequencing, and state transitions flow through one place, so the system stays legible and debuggable.
3. **Messages are typed contracts, not free text.** Agents communicate through a strict message schema with versioned payloads. This is what makes the communication "orderly" — a downstream agent can trust the shape of what it receives.
4. **Nothing irreversible without a human.** Scraping, matching, scoring, and drafting all run autonomously. Anything that touches the outside world in your name (submitting an application, sending an email) stops at an approval gate.
5. **Guardrails are enforced in code, not in prompts.** Hooks sit between the agent's intent and the actual side effect. A prompt can be talked out of a rule; a hook cannot.
6. **Context compounds.** Every run writes structured learnings back to a persistent store, so the system's judgment (what's a good match, which outreach works) improves with use rather than starting cold each time.
7. **Platform-agnostic core.** The architecture is described in terms of roles and contracts. It can be implemented on the Claude Agent SDK, a Python orchestration framework (LangGraph / CrewAI / AutoGen), or a custom loop — the component boundaries stay the same.

---

## 2. System at a glance

```
                          ┌─────────────────────────────┐
                          │        ORCHESTRATOR          │
                          │  (state machine + router)    │
                          └──────────────┬──────────────┘
                                         │  typed messages
        ┌────────────┬───────────┬───────┴───────┬────────────┬──────────────┐
        ▼            ▼           ▼               ▼            ▼              ▼
   ┌─────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐ ┌──────────┐ ┌──────────────┐
   │ Profile │ │ Discovery│ │  Match   │  │ Contact  │ │ Outreach │ │ Application  │
   │  Agent  │ │  Agent   │ │  Agent   │  │  Agent   │ │  Agent   │ │   Agent      │
   └─────────┘ └──────────┘ └──────────┘  └──────────┘ └──────────┘ └──────────────┘
                                                │            │              │
                                                ▼            ▼              ▼
                                          ┌───────────────────────────────────┐
                                          │      HOOKS  /  GUARDRAIL LAYER      │  ◀── enforced in code
                                          │  rate limits · ToS · compliance ·  │
                                          │  dedup · PII · APPROVAL GATE        │
                                          └──────────────────┬──────────────────┘
                                                             │ approved actions only
                                                             ▼
                                                  external world (job boards,
                                                  email, ATS) + Follow-up Agent
                                                             │
                                                             ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │                          SHARED CONTEXT STORE                                  │
   │  profile · opportunities · contacts · outreach log · feedback · learnings      │
   └──────────────────────────────────────────────────────────────────────────────┘
                                                             │
                                                             ▼
                                                   Reporter Agent → you (status reports)
```

The flow mirrors your mind map, read bottom-up: your materials seed a profile → search criteria drive discovery → opportunities get matched → matches branch into auto-apply and contact-scraping → contacts get cold emails → follow-ups run on a cadence → everything reports back to you.

---

## 3. The agent roster

Each agent is a pure function of `(input message, context) → output message + context writes`. None of them sends anything to the outside world directly — they produce *proposed actions* that the hook layer executes only after guardrails (and, for outbound, your approval) pass.

| # | Agent | Single responsibility | Consumes | Produces |
|---|-------|----------------------|----------|----------|
| 0 | **Profile Agent** | Turn your raw materials into a structured, queryable profile + a search criteria spec | Resume, Substack, website, GitHub, project descriptions | `ProfileDoc`, `SearchCriteria` |
| 1 | **Discovery Agent** | Find candidate opportunities matching the criteria | `SearchCriteria` | `RawOpportunity[]` |
| 2 | **Match Agent** | Score & rank each opportunity against the profile; explain the fit | `RawOpportunity[]`, `ProfileDoc` | `ScoredOpportunity[]` |
| 3 | **Contact Agent** | For high-scoring roles, identify relevant people (recruiters, hiring managers, team) | `ScoredOpportunity` | `Contact[]` |
| 4 | **Outreach Agent** | Draft personalized cold emails (never send — draft only) | `Contact`, `ScoredOpportunity`, `ProfileDoc` | `DraftEmail` (pending approval) |
| 5 | **Application Agent** | Assemble a tailored application package (resume variant, cover letter, form answers) | `ScoredOpportunity`, `ProfileDoc` | `DraftApplication` (pending approval) |
| 6 | **Follow-up Agent** | Track sent outreach/apps and draft timed follow-ups | `OutreachLog`, time triggers | `DraftFollowup` (pending approval) |
| 7 | **Reporter Agent** | Compile what the agents did into a status report **for you** | All context writes since last report | `StatusReport` |

Notes on boundaries that matter:

- **Profile Agent runs rarely** (when your materials change), the rest run per cycle. It's the foundation layer of your sketch.
- **Match Agent is the gate before any human-facing work.** Only opportunities above a score threshold proceed to Contact/Application, which keeps volume — and your approval queue — sane.
- **Outreach, Application, and Follow-up only ever produce drafts.** This is the structural reason your "approval gates" choice is enforceable: these agents have no send capability at all. Sending is a separate, gated step owned by the hook layer.
- **Reporter is read-only.** It never triggers actions; it just narrates. This is the "notifications = report to myself" clarification baked into the design.

---

## 4. The orchestrator

The orchestrator is the spine. It does five things and nothing else:

1. **Owns the state machine.** Each opportunity moves through an explicit lifecycle: `discovered → scored → (rejected | shortlisted) → contacts_found → drafted → awaiting_approval → approved → sent → following_up → closed`. The orchestrator is the only component that advances state.
2. **Routes messages.** It reads an agent's output, validates it against the schema, decides the next agent(s), and dispatches. Routing rules are declarative (a table of `state → next agent`), not buried in agent logic.
3. **Sequences and parallelizes.** Independent work fans out (e.g., score 50 opportunities concurrently); dependent work serializes (can't draft outreach before contacts exist). The orchestrator enforces the dependency graph.
4. **Manages the approval queue.** When an agent produces a `pending-approval` artifact, the orchestrator parks the opportunity in `awaiting_approval` and surfaces it to you. On your decision, it resumes or discards.
5. **Handles failure & retries.** Timeouts, schema-validation failures, and tool errors are caught here — not inside agents. It applies retry-with-backoff, dead-letters poison messages, and never silently drops work.

**Orchestration model:** a *blackboard + state machine* pattern. The "blackboard" is the context store (Section 6); the state machine drives progression. This is deliberately not a free-form "agents decide who to call next" swarm — that's what creates disorderly, hard-to-debug systems. Every transition is logged with a trace ID so any opportunity's full history is reconstructable.

**Why centralized over peer-to-peer:** with 8 agents, peer-to-peer messaging is up to ~28 possible channels to reason about; centralized routing is 8. It also gives you exactly one place to insert guardrails, logging, and approval — which is the whole point of the hook layer.

---

## 5. Inter-agent message protocol

Every message is the same envelope. Agents validate on receipt and refuse malformed input (a guardrail in itself).

```json
{
  "msg_id": "uuid",
  "trace_id": "uuid",            // ties all messages for one opportunity together
  "schema_version": "1.0",
  "from_agent": "match",
  "to_agent": "contact",
  "intent": "find_contacts",      // verb the receiver must support
  "opportunity_id": "opp_123",
  "payload": { },                  // typed per intent; validated against a registered schema
  "context_refs": ["profile:v3", "criteria:v2"],  // pointers, not copies
  "created_at": "2026-06-02T10:00:00Z",
  "requires_approval": false
}
```

Three rules make communication orderly:

- **Pointers, not payloads, for shared state.** Agents reference context by ID/version (`profile:v3`) rather than passing big blobs around. The receiver pulls what it needs from the store. This keeps messages small and guarantees everyone reads the same canonical version.
- **Versioned payload schemas.** Each `intent` has a registered JSON schema. Bump `schema_version` to evolve without breaking older artifacts. The orchestrator rejects unversioned or unknown intents.
- **Idempotency by `msg_id`.** Re-delivering a message (after a retry/crash) is safe; the orchestrator dedups on `msg_id`, so an agent never double-acts.

---

## 6. The shared context store (the part that "builds over time")

This is the long-term memory that makes the system improve. Conceptually it's a versioned, append-friendly store with a few logical collections:

| Collection | What it holds | Why it compounds value |
|-----------|---------------|------------------------|
| `profile` | Structured you: skills, experience, writing samples, project narratives, preferences | Versioned, so drafts always reflect your latest materials |
| `criteria` | Active search parameters (titles, locations, comp, remote, stage, exclusions) | You tune it; the system learns which tweaks improve match quality |
| `opportunities` | Every role seen, its score, fit rationale, lifecycle state | Dedup source; prevents re-applying; trend data over time |
| `contacts` | People found, source, relationship to a role, do-not-contact flags | Avoids double-outreach; builds a reusable network graph |
| `outreach_log` | Every draft, approval decision, send, open/reply (if trackable) | Feeds the Follow-up Agent and outreach-effectiveness learning |
| `feedback` | Your approve/edit/reject decisions + edits you made to drafts | **The learning signal** — see below |
| `learnings` | Distilled patterns: "roles like X score high but never reply", "your edits always shorten the intro" | Injected into agent prompts on future runs |

**How learning actually happens (no model training required):**

1. Every approval-gate decision is captured as structured feedback: approved as-is, approved with edits (diff stored), or rejected (with optional reason).
2. A lightweight **distillation step** (can be the Reporter Agent or a dedicated nightly job) turns raw feedback into compact, human-readable rules in `learnings`.
3. Those rules are injected into the relevant agent's context on the next run (e.g., Outreach Agent always receives your last 10 edits + distilled style rules). The agents get visibly better at producing things you approve without edits.

This is retrieval-and-inject learning, which is debuggable and reversible — you can read exactly why an agent changed behavior, and delete a bad learning. Keep it scoped per-agent so the Match Agent's learnings don't pollute the Outreach Agent.

---

## 7. Hooks & guardrails

Hooks are interception points the orchestrator runs *around* agent actions. They are the enforced boundary between what an agent wants to do and what actually happens. Grouped by where they fire:

**Pre-action hooks (before an agent runs)**
- **Rate limiter / budget gate:** cap discovery queries, scraping requests, and LLM token spend per cycle. Hard stop, not a suggestion.
- **Input validator:** reject malformed/oversized inputs before they reach an agent.
- **Source-policy hook:** see Section 8 — blocks discovery/scraping from disallowed sources or above allowed frequency.

**Post-action hooks (after an agent produces output, before it's accepted)**
- **Schema validator:** output must match the registered schema or it's rejected/retried.
- **Dedup hook:** drop opportunities/contacts already in the store; never contact the same person twice for the same role.
- **PII & secrets hook:** strip/redact anything sensitive from logs and reports; enforce do-not-contact lists.
- **Compliance hook (outbound only):** every `DraftEmail` must contain the CAN-SPAM-required elements (accurate identity, honest subject, physical postal address, working opt-out) before it can even enter the approval queue. Drafts failing this are bounced back to the Outreach Agent. (See Section 8.)

**The approval gate (the human hook)**
- Any artifact with `requires_approval: true` halts in `awaiting_approval`.
- You see the full draft + the agent's rationale + the target, and choose **approve / edit & approve / reject**.
- Only after approval does the orchestrator hand the artifact to the **send executor** — the *only* component with outbound credentials. Agents never hold send capability.
- Your decision and any edits are written to `feedback` (Section 6), closing the learning loop.

**Kill switches & circuit breakers**
- A global pause flag stops all outbound activity instantly.
- Circuit breakers trip per-source (e.g., too many scrape failures → back off that source) and per-volume (e.g., more than N sends queued in a day → require a batch confirmation).

---

## 8. Compliance & platform-risk guardrails (grounded in current rules)

These are not optional polish — they're the difference between a useful tool and account bans / legal exposure. Bake them into the hook layer.

**Cold email (Outreach + Follow-up Agents).** US cold email is governed by the CAN-SPAM Act. The compliance hook must verify every outbound email includes: accurate "From"/header info and a non-deceptive subject line, a valid physical postal mailing address, and a clear, working opt-out mechanism — and the system must honor opt-outs within 10 business days (maintain a suppression list that the dedup/do-not-contact hook reads). Penalties run to ~$53,000 **per email**, and liability attaches even when a tool sends on your behalf, so this is enforced in code, not left to the drafting prompt. Practically, also send from a properly authenticated domain (SPF, DKIM, DMARC) and keep volume low to stay under spam-rate thresholds. If you ever target EU/UK recipients, GDPR/PECR add a consent/legitimate-interest layer — keep those recipients out of scope unless you add that handling.

**Scraping & discovery (Discovery + Contact Agents).** Scraping *public* data has been held not to violate the US CFAA (the hiQ v. LinkedIn line of cases), but that's a narrow criminal-law point. LinkedIn's and many platforms' Terms of Service still prohibit automated scraping, and they enforce it with account bans and civil contract claims — LinkedIn has won on contract/ToS grounds. Design implications, enforced by the source-policy hook:
- **Prefer official, sanctioned sources first:** job-board APIs, ATS/job feeds, RSS, partner APIs, and sites whose ToS permit automated access. These are the default discovery channels.
- **Treat ToS-restricted platforms as off by default.** If you choose to use one, do it through human-in-the-loop assist (you're in the session) rather than headless mass automation, respect `robots.txt`, throttle hard, and never use fake accounts.
- **Keep a per-source policy table** (allowed / human-assisted / blocked) that the hook reads before any fetch. Make the conservative choice the default.

None of this is legal advice — it's a description of the constraints the system should encode. For anything high-stakes, confirm with a professional.

---

## 9. End-to-end flow (one cycle)

1. **(Occasional) Profile refresh.** You update materials → Profile Agent rebuilds `ProfileDoc` + proposes `SearchCriteria` → you confirm criteria (a lightweight approval).
2. **Discovery.** Orchestrator triggers Discovery Agent against allowed sources → `RawOpportunity[]` → dedup hook drops known ones → stored.
3. **Matching.** Match Agent scores each against the profile → `ScoredOpportunity[]`. Below-threshold roles are archived with a reason; above-threshold are shortlisted.
4. **Branch (parallel), per shortlisted role:**
   - **Apply track:** Application Agent assembles a tailored package → compliance/quality hooks → `awaiting_approval`.
   - **Contact track:** Contact Agent finds people → Outreach Agent drafts emails → CAN-SPAM hook → `awaiting_approval`.
5. **Approval.** You review the queue (drafts + rationale + targets). Approve / edit / reject. Decisions logged to `feedback`.
6. **Send.** Send executor dispatches only approved items via authenticated channels. State → `sent`.
7. **Follow-up.** Follow-up Agent watches for replies/elapsed time and drafts timed nudges → back through the approval gate.
8. **Report.** Reporter Agent compiles the cycle into a status report **to you**: what was discovered, scored, drafted, what's awaiting approval, what was sent, reply rates, and surfaced learnings. Delivered on your chosen cadence.
9. **Learn.** Distillation step turns this cycle's feedback into `learnings` injected next cycle.

---

## 10. Cross-cutting concerns

- **Observability:** every message and state transition logged with `trace_id`; a single opportunity's life is fully reconstructable. Track per-agent success/error/latency and per-cycle volume/cost.
- **Idempotency & crash recovery:** because state lives in the store and messages are idempotent, a crash mid-cycle resumes cleanly — no double-sends, no lost opportunities.
- **Cost control:** token/$ budget is a first-class guardrail (Section 7); Reporter surfaces spend each cycle.
- **Testing:** each agent is independently unit-testable via its message contract (feed input, assert output schema). Guardrail hooks get their own tests with adversarial inputs (e.g., a draft missing an opt-out must be rejected). End-to-end runs use a sandbox mode where the send executor is a no-op that logs instead of sends.
- **Secrets:** outbound credentials live only with the send executor, never in agents or context store. Context store redacts PII in anything the Reporter surfaces.
- **Extensibility:** adding an agent = register its intents/schemas + add routing rules. No existing agent changes. (e.g., a future "Interview-prep Agent" slots in after `sent`.)

---

## 11. Suggested build sequence (for when you implement)

This doc is the architecture; here's the order that de-risks it fastest:

1. **Context store + message schema + orchestrator skeleton** — the spine. Stub agents that echo.
2. **Profile + Discovery + Match** — get real, scored opportunities flowing into the store (read-only, zero outbound risk).
3. **Approval gate + Reporter** — make the system observable and human-controllable before it can act.
4. **Application + Outreach (draft-only)** — drafts into the approval queue; nothing sends yet.
5. **Hook layer hardening** — compliance, rate limits, dedup, source policy; test with adversarial inputs.
6. **Send executor + Follow-up** — turn on outbound, behind the gate, in sandbox first, then live at low volume.
7. **Learning distillation loop** — close the feedback→learnings→injection cycle.

Build outbound last and behind the gate from day one; everything before step 6 is safe to run freely.

---

## 12. Open questions to resolve before building

- Which job sources are in scope, and what are their ToS/API realities? (Drives the source-policy table.)
- Email channel: your own authenticated domain vs. a provider — affects deliverability and CAN-SPAM setup.
- How tailored should applications be — one master resume with light tailoring, or per-role variants?
- Approval cadence: real-time per draft, or batched review once/twice a day?
- Where does the system run — your machine on a schedule, or always-on? (Affects the time-triggered Follow-up Agent.)
- Report delivery channel and frequency (email to yourself, a dashboard, a daily digest?).

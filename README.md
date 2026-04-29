# Supply Chain Guard

An **agentic workflow engine** that detects supply chain disruptions, evaluates recovery options, and surfaces cost-justified resolution plans for human approval — all within seconds — freeing operations teams from hours of manual triage.

Routing and financial decisions are deterministic Python. LLM agents provide reasoning narrative at each step. The human approves the final plan. **Predictable by design — because financial decisions require auditability, not autonomy.**

---

## Table of Contents

1. [The Problem](#the-problem)
2. [The Solution](#the-solution)
3. [Real-World Example](#real-world-example)
4. [Architecture](#architecture)
5. [Agent Pipeline](#agent-pipeline)
6. [The Negotiation Loop](#the-negotiation-loop)
7. [Technology Choices](#technology-choices)
8. [Project Structure](#project-structure)
9. [Data Models](#data-models)
10. [API Reference](#api-reference)
11. [Getting Started](#getting-started)
12. [Configuration](#configuration)
13. [Running the Loop Scenario](#running-the-loop-scenario)
14. [Observability with LangSmith](#observability-with-langsmith)
15. [ERP & TMS Integration](#erp--tms-integration)

---

## The Problem

Global supply chains break constantly. A vessel is delayed, a factory goes dark, a port is congested. When it happens, an operations team member has to:

1. Notice the alert (often via email or a portal)
2. Manually check inventory: *"How many days before the production line stops?"*
3. Call 3–5 freight brokers for spot rates
4. Check each carrier against a compliance blacklist
5. Calculate whether the air freight cost is justified vs the penalty for a late delivery
6. Get finance sign-off
7. Book the carrier

This process takes **2–8 hours**. A factory shutdown costs **$50,000–$500,000 per day**. Every hour of manual triage is money lost.

---

## The Solution

Supply Chain Guard replaces the manual triage loop with an **autonomous agent pipeline**:

- A disruption event arrives via webhook (from an ERP, TMS, or manual POST)
- 4 specialist AI agents run in sequence, each with a defined role and decision authority
- If the Financial Controller rejects a proposal (too expensive), the Logistics Strategist is automatically retried with the next best option — no human needed until a valid plan is ready
- The final resolution (carrier, cost, compliance status, cost-vs-penalty summary) is surfaced to a human reviewer for a single approval click
- Once approved, the ERP receives the response and handles the TMS booking using its own integration

**Result:** Manual triage time drops from hours to **under 2 minutes**. The human reviewer only sees pre-validated, cost-justified options.

---

## Real-World Example

> A vessel carrying SKU-9921 (a critical automotive component) is delayed by 7 days. The production line hard deadline is May 8. The factory shutdown cost is $50,000/day.

**Without Supply Chain Guard:**
- Ops team notices alert → opens ERP → checks inventory → emails broker → waits for quotes → finance review → 4 hours later, books a flight

**With Supply Chain Guard:**

```
[00:00] Webhook received — vessel delay, SKU-9921, +7 days
[00:01] Inventory Analyst: 3 days of buffer remaining, hard deadline May 8, CRITICAL
[00:02] Logistics Strategist (iter 1): Proposes Express Air Freight — $12,000, 2 days
[00:03] Financial Controller: REJECTED — $12,000 exceeds budget of $9,500
[00:03] Logistics Strategist (iter 2): Proposes Sea-Air Logistics — $7,500, 5 days
[00:04] Financial Controller: APPROVED — $7,500 saves $242,500 vs penalty
[00:04] Compliance Auditor: CLEARED — insurance valid, not blacklisted
[00:04] Status: pending_approval — awaiting human sign-off
```

Total time: **~90 seconds**. The reviewer sees a single, pre-validated recommendation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        External Systems                              │
│   ERP (erp_system_a/b/c)    TMS webhook    Manual API call          │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ POST /api/v1/events/disruption
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                             │
│                                                                      │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────┐               │
│  │ Disruptions │   │  Approvals   │   │  Carriers  │               │
│  │   /events   │   │  /approvals  │   │ /carriers  │               │
│  └──────┬──────┘   └──────────────┘   └────────────┘               │
│         │ background_task                                            │
│         ▼                                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │               LangGraph Pipeline (StateGraph)                 │   │
│  │                                                               │   │
│  │  inventory_analyst → logistics_strategist → financial_ctrl   │   │
│  │                              ▲                    │           │   │
│  │                              └─── REJECTED ───────┘           │   │
│  │                                   (loop up to 5x)             │   │
│  │                                        │ APPROVED             │   │
│  │                              compliance_auditor               │   │
│  │                                        │                      │   │
│  │                              resolved / escalated             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│         │                                                            │
│         ▼                                                            │
│  SQLite DB (SQLAlchemy async)   SSE event bus (real-time updates)    │
└─────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
        LangSmith (trace every agent run, loop, decision)
```

---

## Agent Pipeline

The pipeline is a **LangGraph `StateGraph`** — a directed graph where each node is an agent function and edges are either fixed or conditional (routing logic).

```
inventory_analyst
        │
        ▼
logistics_strategist ◄─────────────────────┐
        │                                   │
        ▼                                   │ (REJECTED — try next carrier)
financial_controller ───────────────────────┘
        │
        │ (APPROVED)
        ▼
compliance_auditor
        │
   ┌────┴────┐
   ▼         ▼
resolved   escalate
   │         │
   ▼         ▼
  END       END
```

### Agent Roles

| Agent | Role | Decision |
|---|---|---|
| **Inventory Analyst** | Reads on-hand qty, safety stock, production schedule. Calculates days of buffer before shutdown. | Sets `urgency_level`, `days_of_buffer`, `can_wait` |
| **Logistics Strategist** | Selects best carrier from live DB. Sorts by reliability DESC — tries best quality first, steps down on each rejection. | Sets `proposed_carrier`, `proposed_cost`, `proposed_transit_days` |
| **Financial Controller** | Compares cost vs penalty. Approves if `cost ≤ budget AND savings > 0`. Pure deterministic math — no LLM hallucination risk on the decision itself. | Sets `financially_approved` |
| **Compliance Auditor** | Checks carrier against blacklist, insurance expiry, certifications. | Sets `compliance_cleared` |
| **Orchestrator** | Routing logic — increments `iteration`, routes to next node or escalates at `max_iterations`. | Not an LLM — pure Python routing functions |

---

## The Negotiation Loop

The most important design pattern in this system is the **financial rejection loop**.

### Why a loop instead of just picking the cheapest carrier?

Cheapest-first leads to two problems:
1. Cheap carriers are often slow — they may not meet the hard deadline
2. You miss the business trade-off: sometimes a more expensive carrier saves far more in avoided penalties

Supply Chain Guard instead tries **best quality first** (highest reliability score), then steps down to cheaper options only when the Financial Controller rejects the cost:

```
Iteration 1: Express Air Freight (reliability 92, $12,000/unit)
             → Financial Controller: REJECTED ($12k > $9.5k budget)

Iteration 2: Sea-Air Logistics (reliability 85, $7,500/unit)
             → Financial Controller: APPROVED ($7.5k ≤ $9.5k, saves $242.5k)

Iteration 3+: Would try cheaper options (Regional Road at $3,200) if needed
```

The loop is capped at `max_iterations` (default: 5). If no carrier passes financial review, the event is **escalated** to a human with the full audit trail.

### Loop mechanics (LangGraph)

```python
# orchestrator.py — routing function after financial_controller node
def should_continue(state) -> str:
    if state["financially_approved"]:
        return "compliance_auditor"      # ✓ approved — move forward
    next_iter = state["iteration"] + 1
    if next_iter > state["max_iterations"]:
        return "escalate"                # ✗ exhausted all options
    state["iteration"] = next_iter
    return "logistics_strategist"        # ↺ retry with next carrier

# logistics_strategist.py — carrier selection by iteration index
pool = sorted(viable_carriers, key=lambda x: (-x["reliability_score"], x["rate_per_unit"]))
idx  = min(state["iteration"] - 1, len(pool) - 1)
best = pool[idx]   # iter 1→index 0 (best), iter 2→index 1, etc.
```

---

## Technology Choices

### Why LangGraph?

Supply chain triage is a **business process with financial and compliance consequences** — it needs to be predictable, auditable, and bounded, not creative. LangGraph models the workflow as an explicit state machine where every node, every transition, and every exit condition is declared in code:

```python
graph.add_edge("inventory_analyst", "logistics_strategist")
graph.add_edge("logistics_strategist", "financial_controller")
graph.add_conditional_edges(
    "financial_controller",
    should_continue,          # plain Python function — fully testable
    {
        "compliance_auditor": "compliance_auditor",      # approved
        "logistics_strategist": "logistics_strategist",  # rejected — loop back
        "escalate": "escalate",                          # max iterations hit
    },
)
```

**How it's used in this project:**

| LangGraph concept | How it's used here |
|---|---|
| `StateGraph` | The entire pipeline — 4 agent nodes + 2 terminal nodes |
| `SupplyChainState` TypedDict | Typed state shared across all nodes — `proposed_cost`, `financially_approved`, `iteration`, `audit_trail`, etc. |
| Fixed edges | `inventory_analyst → logistics_strategist → financial_controller` always in order |
| Conditional edges | After `financial_controller`: approved → `compliance_auditor`, rejected → back to `logistics_strategist`, exhausted → `escalate` |
| `should_continue()` | Pure Python routing — increments `iteration`, checks `max_iterations`, returns next node name |
| Terminal nodes | `resolved` / `escalate` set `resolution_status` before `END` |

The routing logic is plain Python with no LLM involved — it can be unit tested in isolation. The LLM is only used to generate reasoning text (the `finding` in each audit entry), never for routing decisions. This separation is what makes the system trustworthy for financial decisions.

### Why LangSmith?

Every agent run — including loops — is traced automatically. For each disruption event you can see:
- Which agents ran, in what order, how many times
- The exact prompt sent to the LLM and the response received
- Where a loop fired (Logistics Strategist appears twice in the trace)
- Token usage and latency per node

This is critical for debugging and for demonstrating to stakeholders that the system made the right decisions.

### LLM Provider — Bring Your Own

The system is provider-agnostic. Any LangChain-compatible LLM works — set `LLM_PROVIDER` and `LLM_MODEL` in `.env`:

| Provider | `LLM_PROVIDER` | Recommended model | Notes |
|---|---|---|---|
| **Groq** | `groq` | `llama-3.1-8b-instant` | Free tier, sub-second latency, 500k tokens/day |
| **OpenAI** | `openai` | `gpt-4o-mini` | Paid, reliable, widely available |
| **Anthropic** | `anthropic` | `claude-3-5-haiku-20241022` | Paid, strong reasoning |
| **Ollama** | `ollama` | `llama3.2` | Fully local, no API key, no cost |

The agents only need structured text output (approve/reject decisions with reasoning) — a small/fast model is sufficient and far cheaper than a frontier model.

### Why FastAPI + SQLAlchemy async?

- FastAPI's `BackgroundTasks` lets the webhook return instantly (`202 Accepted`) while the pipeline runs asynchronously — no blocking the caller
- SQLAlchemy async sessions with aiosqlite allow the pipeline to read/write DB state without blocking the event loop
- Pydantic v2 schemas give request/response validation at the API boundary

---

## Project Structure

```
supply-chain-guard/
├── config/
│   ├── agents.yaml          # Agent roles, goals, backstories
│   └── tasks.yaml           # Task prompts and expected outputs
├── data/
│   └── supply_chain_guard.db  # SQLite database (auto-created)
├── scripts/
│   ├── seed_db.py           # Populate DB with carriers, inventory, rules
│   ├── e2e_test.py          # End-to-end HTTP test
│   └── test_pipeline_direct.py  # Direct pipeline test (no HTTP)
├── src/
│   ├── main.py              # FastAPI app factory + LangSmith init
│   ├── config.py            # Settings (env vars, LLM factory)
│   ├── database.py          # SQLAlchemy engine + session factories
│   ├── run_api.py           # Uvicorn entry point
│   ├── agents/
│   │   ├── inventory_analyst.py
│   │   ├── logistics_strategist.py
│   │   ├── financial_controller.py
│   │   ├── compliance_auditor.py
│   │   └── orchestrator.py  # Routing functions (no LLM)
│   ├── api/
│   │   ├── disruptions.py   # Webhook + pipeline runner + SSE
│   │   ├── approvals.py     # Human approval endpoints
│   │   ├── carriers.py      # Carrier CRUD
│   │   ├── inventory.py     # Inventory CRUD
│   │   ├── financials.py    # Financial rules CRUD
│   │   └── __init__.py      # Router registration
│   ├── adapters/
│   │   ├── erp_input.py     # ERP payload transform adapters
│   │   └── tms_output.py    # TMS carrier booking writeback
│   ├── graph/
│   │   ├── pipeline.py      # LangGraph StateGraph definition
│   │   └── state.py         # SupplyChainState TypedDict
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   └── tools/               # LangChain tools (DB query wrappers)
└── .env                     # Environment variables (not committed)
```

---

## Data Models

### Disruption Event lifecycle

```
received → processing → pending_approval → approved / rejected
                    └──→ escalated          (max iterations hit or compliance failed)
                    └──→ escalated_stale_data  (inventory data too old)
                    └──→ error              (pipeline exception)
```

### Seed data (scripts/seed_db.py)

| Carrier | Mode | Transit | Cost/unit | Reliability | Status |
|---|---|---|---|---|---|
| Express Air Freight | air | 2 days | $12,000 | 92 | Active |
| Sea-Air Logistics | sea-air | 5 days | $7,500 | 85 | Active |
| Regional Road Carrier | road | 8 days | $3,200 | 78 | Active |
| Restricted Carrier Co | sea | 20 days | $800 | 40 | **Blacklisted** |

**Financial rule for SKU-9921:**
- Max expedite budget: **$9,500**
- Auto-approve ceiling: $5,000
- Penalty per day: $50,000

**Inventory — SKU-9921:**
- On hand: 1,500 units | Safety stock: 500 units | Days of cover: 3

---

## API Reference

Interactive docs available at `http://localhost:8000/docs` after starting the server.

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/events/disruption` | Submit a disruption event (webhook) |
| `POST` | `/api/v1/events/erp/{source_system}` | ERP-specific webhook with payload transform |
| `GET` | `/api/v1/events/disruption/{event_id}` | Poll event status |
| `GET` | `/api/v1/events/stream/{event_id}` | SSE stream for real-time status updates |
| `GET` | `/api/v1/approvals/pending` | List all events awaiting human approval |
| `GET` | `/api/v1/approvals/{event_id}` | Get resolution plan for an event |
| `POST` | `/api/v1/approvals/{event_id}/approve` | Approve a resolution plan |
| `POST` | `/api/v1/approvals/{event_id}/reject` | Reject a resolution plan |

### Disruption Event Payload

```json
{
  "source_system": "manual",
  "event_type": "vessel_delay",
  "shipment_id": "SHP-001",
  "affected_skus": [
    { "sku": "SKU-9921", "qty": 500 }
  ],
  "original_eta": "2026-05-01T00:00:00Z",
  "revised_eta": "2026-05-08T00:00:00Z",
  "severity": "critical"
}
```

**Response:** `202 Accepted` with `event_id`. Poll the status endpoint or subscribe to the SSE stream.

### Resolution Plan Response (pending_approval)

```json
{
  "event_id": "af9ad0c1-...",
  "recommended_carrier": "Sea-Air Logistics",
  "recommended_mode": "sea-air",
  "estimated_cost": 7500.0,
  "estimated_eta_days": 5,
  "cost_vs_penalty_summary": "Cost $7,500 vs penalty $350,000 (APPROVED) — savings $342,500",
  "audit_trail": [
    { "agent": "Inventory Analyst", "finding": "...", "decision": "3 days buffer, CRITICAL" },
    { "agent": "Logistics Strategist", "finding": "...", "decision": "Proposed Express Air at $12,000" },
    { "agent": "Financial Controller", "finding": "...", "decision": "REJECTED — exceeds $9,500 budget" },
    { "agent": "Logistics Strategist", "finding": "...", "decision": "Proposed Sea-Air at $7,500" },
    { "agent": "Financial Controller", "finding": "...", "decision": "APPROVED — saves $342,500" },
    { "agent": "Compliance Auditor", "finding": "...", "decision": "CLEARED" }
  ],
  "status": "pending_approval"
}
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- An LLM API key — [Groq](https://console.groq.com) (free tier), [OpenAI](https://platform.openai.com), [Anthropic](https://console.anthropic.com), or [Ollama](https://ollama.com) running locally
- Optional: [LangSmith account](https://smith.langchain.com) for tracing

### 1. Clone and install

```bash
git clone https://github.com/harimanda123/supply-chain-guard.git
cd supply-chain-guard
uv sync
```

### 2. Configure environment

Create a `.env` file in the project root:

```ini
# App
APP_ENV=development
SECRET_KEY=change-me-in-production

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/supply_chain_guard.db

# LLM — choose one provider
LLM_PROVIDER=groq                        # groq | openai | anthropic | ollama
LLM_MODEL=llama-3.1-8b-instant           # any model supported by the provider
GROQ_API_KEY=gsk_your_key_here           # only the active provider's key is needed
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# OLLAMA_BASE_URL=http://localhost:11434  # Ollama only, no key needed

# LangSmith (optional — remove block to disable tracing)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_PROJECT=supply-chain-guard
```

### 3. Initialise the database

```bash
uv run --with alembic alembic upgrade head
uv run python -m scripts.seed_db
```

### 4. Start the API server

```bash
uv run python -m src.run_api
```

Server starts at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`.

### 5. Submit a test disruption

```bash
curl -X POST http://localhost:8000/api/v1/events/disruption \
  -H "Content-Type: application/json" \
  -d '{
    "source_system": "manual",
    "event_type": "vessel_delay",
    "shipment_id": "SHP-TEST-001",
    "affected_skus": [{"sku": "SKU-9921", "qty": 500}],
    "original_eta": "2026-05-01T00:00:00Z",
    "revised_eta": "2026-05-08T00:00:00Z",
    "severity": "critical"
  }'
```

Poll status with the `event_id` from the response:

```bash
curl http://localhost:8000/api/v1/events/disruption/{event_id}
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` \| `openai` \| `anthropic` \| `ollama` |
| `LLM_MODEL` | `llama-3.1-8b-instant` | Any model name supported by the chosen provider |
| `GROQ_API_KEY` | — | Groq API key (only needed when `LLM_PROVIDER=groq`) |
| `OPENAI_API_KEY` | — | OpenAI API key (only needed when `LLM_PROVIDER=openai`) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (only needed when `LLM_PROVIDER=anthropic`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL (only needed when `LLM_PROVIDER=ollama`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/supply_chain_guard.db` | SQLAlchemy async DB URL |
| `LANGSMITH_TRACING` | `false` | Enable LangSmith tracing (`true`/`false`) |
| `LANGSMITH_API_KEY` | — | LangSmith API key |
| `LANGSMITH_PROJECT` | `supply-chain-guard` | LangSmith project name |


---

## Running the Loop Scenario

The seed data is configured to demonstrate the negotiation loop:

- **Budget:** $9,500 (between Sea-Air at $7,500 ✓ and Express Air at $12,000 ✗)
- **Iteration 1:** Logistics Strategist proposes Express Air (highest reliability, $12k) → Financial Controller **rejects**
- **Iteration 2:** Logistics Strategist steps down to Sea-Air ($7.5k) → Financial Controller **approves**

**To run a clean loop test:**

```bash
# 1. Delete old DB and re-seed with loop scenario data
del data\supply_chain_guard.db          # Windows
# rm data/supply_chain_guard.db         # macOS/Linux

uv run --with alembic alembic upgrade head
uv run python -m scripts.seed_db

# 2. Start server
uv run python -m src.run_api

# 3. Post disruption (use Swagger or curl)
# 4. In LangSmith, open the trace — you will see:
#    logistics_strategist (iter 1) → financial_controller (REJECTED)
#    → logistics_strategist (iter 2) → financial_controller (APPROVED)
#    → compliance_auditor → resolved
```

---

## Observability with LangSmith

Every pipeline run is traced automatically when `LANGSMITH_TRACING=true`.

**What you can see in LangSmith:**

- The full agent execution graph with timing per node
- Each LLM prompt and response (expandable)
- Loop iterations — Logistics Strategist and Financial Controller appear **twice** in a loop trace
- Token usage per agent call
- Error details if the pipeline fails

**View traces:** https://smith.langchain.com → Projects → `supply-chain-guard`

**Important:** LangSmith env vars must be set **before** any LangChain imports. The app handles this in `src/main.py` by reading `.env` with `dotenv_values()` at the very top of the file before the rest of the imports.

---

## JSON Schemas for ERP Integration

All API contracts are published as JSON Schema (Draft 2020-12), generated directly from the Pydantic models. ERP teams use these to validate payloads client-side and auto-generate strongly-typed client code before writing a single line of integration code.

### Schema files (`schemas/`)

| File | Used for |
|---|---|
| [disruption-event-create.json](schemas/disruption-event-create.json) | Payload to POST when submitting a disruption |
| [disruption-event-response.json](schemas/disruption-event-response.json) | Response from the submit and status endpoints |
| [resolution-plan.json](schemas/resolution-plan.json) | Response from `GET /approvals/{event_id}` — the recommended carrier, cost, audit trail |
| [approval-request.json](schemas/approval-request.json) | Payload to POST when approving or rejecting |
| [approval-response.json](schemas/approval-response.json) | Confirmation response after approve/reject |
| [carrier.json](schemas/carrier.json) | Carrier record structure |

### Regenerate schemas

If a model changes, re-export:

```bash
uv run python scripts/export_schemas.py
```

### Using schemas in an ERP integration

**Python (jsonschema):**
```python
import json, jsonschema, requests

schema = json.load(open("schemas/disruption-event-create.json"))
payload = {
    "source_system": "erp_system_a",
    "event_type": "vessel_delay",
    "shipment_id": "SHP-001",
    "affected_skus": [{"sku": "SKU-9921", "qty": 500}],
    "original_eta": "2026-05-01T00:00:00Z",
    "revised_eta": "2026-05-08T00:00:00Z",
    "severity": "critical"
}
jsonschema.validate(payload, schema)   # raises if invalid
requests.post("http://supply-chain-guard/api/v1/events/disruption", json=payload)
```

**Java / .NET / other:** Import the `.json` files into any JSON Schema-compatible validator (e.g. `networknt/json-schema-validator` for Java, `Newtonsoft.Json.Schema` for .NET).

---

## ERP & TMS Integration

### Integration Model — Pull, Not Push

Supply Chain Guard uses a **pull model**: the ERP calls Supply Chain Guard's API to submit disruptions and retrieve approved resolution plans. Supply Chain Guard does not push bookings to any TMS — the ERP already has the approved plan and handles the downstream booking itself.

```
ERP  →  POST /api/v1/events/erp/{source_system}    submit disruption
ERP  →  GET  /api/v1/approvals/pending              poll for ready plans
ERP  →  POST /api/v1/approvals/{event_id}/approve   confirm approval
ERP  ←  response: carrier, mode, cost, transit days, audit trail
ERP  →  creates TMS booking using its own integration
```

This keeps Supply Chain Guard stateless after approval. The ERP owns retry logic, booking confirmation, and error handling — it does not need to grant Supply Chain Guard outbound access to any TMS.

---

## License

MIT

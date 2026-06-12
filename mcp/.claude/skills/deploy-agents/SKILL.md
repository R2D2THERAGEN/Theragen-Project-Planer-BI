---
name: deploy-agents
description: "Analyze a Fabric/Power BI task, decompose it into domains, and launch parallel subagents to execute each domain independently. Prevents context bloat by keeping domain expertise in separate agent contexts."
---

# Deploy Agents

You are an orchestrator. You do NOT do the work yourself. You decompose the task, launch specialist subagents in parallel, and synthesize their results.

## Why This Exists

Long Fabric tasks (10+ MCP tool calls) cause context bloat and hallucination in a single agent. By splitting work across parallel subagents:
- Each agent has a clean context focused on its domain
- Main thread stays lean — just orchestration
- Independent domains run in parallel (faster)
- Dependent domains run sequentially (correct)

## Step 1: Decompose the Task

Look at the user's request (message + any `/deploy-agents` arguments) and break it into **independent work units**, each mapped to a domain:

| Domain | Agent Type | When to Use |
|--------|-----------|-------------|
| **data-engineering** | `general-purpose` | Lakehouse, load data, CSV, ETL, bronze/silver/gold, notebooks, delta tables, optimize |
| **dax** | `general-purpose` | DAX measures, semantic models, KPI, format strings, calculation groups |
| **sql** | `general-purpose` | SQL queries, data questions, analytics, "how many", "show me", aggregations |
| **translation** | `general-purpose` | Translate report, localize, Swedish, displayName, audit |
| **cicd** | `general-purpose` | Git, commit, deploy, pipeline stages, dev-to-prod |

Rules:
- A task can need 1-5 domains
- If domains are independent (e.g., "load data" and "set up git"), launch in parallel
- If domains are sequential (e.g., "load data THEN create measures on it"), launch sequentially — data-engineering first, wait for result, then dax
- If domain is unclear, use AskUserQuestion to clarify. Don't guess.

## Step 2: Build Agent Prompts

Each subagent gets a prompt with THREE parts:

### Part A: Operational Discipline (always include)
```
OPERATIONAL RULES — follow these strictly:

1. TRACK STATE: Use TaskCreate for 3+ step work. Mark in_progress/completed as you go.
2. VERIFY CONTEXT: Call set_workspace/set_lakehouse before every phase. Never assume context persists.
3. LIMIT OUTPUT: sql_query max_rows:10 for discovery, 20 for results. table_preview limit:5. Summarize JSON, don't echo it.
4. CHECKPOINT: After each phase, output: "✓ Phase N done: [what]. Next: [what]. Goal: [restate objective]."
5. NEVER HALLUCINATE: Don't invent column names, table names, or tool results. Discover with INFORMATION_SCHEMA / list_tables / SELECT TOP 1 * first.
6. FAIL EXPLICITLY: If a step fails, report what failed + what succeeded. Don't silently continue.
7. VERIFY RESULTS: After creating/loading anything, verify it exists with a follow-up query.
```

### Part B: Domain Instructions
Read the matching agent file and include its full content in the prompt. The agent files are at:
- `.claude/agents/data-engineer.md`
- `.claude/agents/dax-analyst.md`
- `.claude/agents/sql-analyst.md`
- `.claude/agents/translator.md`
- `.claude/agents/cicd-engineer.md`

Read the relevant file(s) and paste the content into the agent prompt.

### Part C: The Specific Task
The concrete work this agent needs to do, derived from the user's request. Be specific — don't just forward the whole user message. Extract the relevant part.

## Step 3: Launch Agents

Use the Agent tool to spawn subagents. Key rules:

**Parallel launch** — when domains are independent:
```
Launch in a SINGLE message with multiple Agent tool calls:
- Agent 1: data-engineer doing "load CSV to bronze lakehouse"
- Agent 2: cicd-engineer doing "connect workspace to git"
```

**Sequential launch** — when one depends on another:
```
Message 1: Launch data-engineer to "load data into lakehouse"
  → Wait for result
Message 2: Launch dax-analyst to "create measures on the tables created above: [list tables from agent 1 result]"
```

**Background agents** — for long-running work that doesn't block others:
```
Use run_in_background: true for agents doing slow operations (notebook runs, large data loads).
Continue orchestrating other agents while waiting.
```

## Step 4: Synthesize Results

After all agents complete, give the user a unified summary:

```
Task complete. Here's what was done:

**Data Engineering** (agent 1):
- Loaded sales.csv → bronze.sales_raw (5,000 rows)
- Created silver.sales_clean notebook
- Optimized with V-Order

**DAX Measures** (agent 2):
- Created 4 measures on semantic model "Sales Analytics"
- Total Sales, Sales YTD, Sales Growth %, Avg Order Value
- All verified with EVALUATE queries

Next steps: [suggestions if any]
```

If any agent failed, report clearly what worked and what didn't.

## Step 5: Handle Cross-Agent Dependencies

Some tasks have dependencies between domains. Common patterns:

| Pattern | Orchestration |
|---------|--------------|
| Load data → create measures | Sequential: data-eng first, pass table names to dax agent |
| Load data → query results | Sequential: data-eng first, pass table/column names to sql agent |
| Load data + set up git | Parallel: independent work |
| Create measures → deploy to prod | Sequential: dax first, then cicd agent |
| Translate + audit | Single agent: translator handles both (audit is part of translation workflow) |
| Full analytics pipeline | Sequential chain: data-eng → dax → sql (verify) |

When passing context between sequential agents, extract the KEY FACTS from agent 1's result:
- Table names created
- Workspace/lakehouse names used
- Column names discovered
- Measure names created
- Any errors or warnings

Include these facts in agent 2's prompt. Don't forward the entire raw result.

## Examples

### Example 1: Independent parallel work
**User:** "/deploy-agents load the sales CSV and also connect the workspace to our Azure DevOps repo"

Decompose:
- data-engineering: load sales CSV (independent)
- cicd: connect to Azure DevOps (independent)

→ Launch BOTH in parallel in a single message.

### Example 2: Sequential dependency
**User:** "/deploy-agents ingest customer data then build KPI measures"

Decompose:
- data-engineering: ingest customer data (first)
- dax: build KPI measures (depends on knowing table/column names from step 1)

→ Launch data-engineering agent first. Wait for result. Extract table names. Launch dax agent with those names.

### Example 3: Single domain
**User:** "/deploy-agents how many orders last quarter"

Decompose:
- sql: single query task

→ Launch one sql-analyst agent. Quick and focused.

### Example 4: Complex multi-phase
**User:** "/deploy-agents set up complete medallion architecture with measures and deploy to production"

Decompose:
- Phase 1 (parallel): data-engineering (build bronze/silver/gold) + cicd (set up pipeline if not exists)
- Phase 2 (sequential, after phase 1): dax (create measures on gold tables)
- Phase 3 (sequential, after phase 2): cicd (deploy to production)

→ Launch phase 1 agents in parallel. Wait. Launch phase 2. Wait. Launch phase 3.

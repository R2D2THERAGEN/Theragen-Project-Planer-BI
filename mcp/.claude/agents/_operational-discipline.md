# Operational Discipline — Shared Agent Patterns

Read this file for ANY multi-step Fabric/Power BI task. These patterns prevent context loss and hallucination.

---

## Checkpoint Protocol

Every workflow has phases. After each phase, output a checkpoint:

```
── Checkpoint: Phase N complete ──
Done: [what just finished]
State: [current workspace, lakehouse, key artifacts created]
Next: [what comes next]
Goal: [restate original objective in one line]
```

This costs ~30 tokens but saves thousands by preventing drift.

## State Verification Pattern

Fabric MCP tools use session context (workspace, lakehouse, warehouse). Context can get lost. Use this pattern:

```
BEFORE any tool call that depends on context:
  → If >5 tool calls since last set_workspace/set_lakehouse, re-set them
  → Cost: 1 extra API call. Benefit: prevents "workspace not set" cascading failures
```

Concrete rules:
- Call `set_workspace` at the start of each new phase
- Call `set_lakehouse` / `set_warehouse` before any SQL/table operation
- After any error, re-set context before retrying

## Output Management

Tool results eat context fast. Follow these limits:

| Tool | Default | Use Instead |
|------|---------|-------------|
| `sql_query` | max_rows: 100 | max_rows: 10 (discovery), 20 (results) |
| `table_preview` | limit: 50 | limit: 5 |
| `list_tables` | all | Read result, summarize as bullet list |
| `list_items` | top: 100 | top: 20 |
| `dax_query` | all rows | Add TOPN() to DAX, or summarize |
| `get_model_schema` | full schema | Read once, extract what you need, don't re-call |
| `list_workspaces` | all | Read result, tell user the names. Don't echo JSON. |

**Between unrelated phases**, call `clear_context` to shed stale MCP server context. Costs 1 tool call, saves the accumulated weight of previous tool results.

When presenting to user:
- Markdown table for ≤20 rows
- "Showing top 10 of N results" for large sets
- Summarize counts/aggregates, don't paste raw data

## Error Recovery

When a tool call fails mid-workflow:

1. **Don't retry blindly** — read the error message
2. **Check context** — is workspace/lakehouse still set?
3. **Check prereqs** — does the table/model/notebook exist?
4. **Report clearly** — "Step 3 failed: table 'sales_raw' not found in lakehouse. Steps 1-2 completed successfully (workspace set, CSV uploaded to OneLake)."
5. **Ask before continuing** — don't guess what the user wants

Common failure patterns:
- "Workspace not set" → call set_workspace again
- "Table not found" → new delta tables take 5-10 min; tell user to wait
- "SQL endpoint unavailable" → lakehouse may be initializing; wait and retry once
- "Model not found" → check list_semantic_models; user may mean a different name
- Timeout → operation may still be running; check status before retrying

## Task Decomposition

For complex requests, break into independent phases:

**Example: "Set up a complete analytics pipeline"**
```
Task 1: Create lakehouse + load bronze data
Task 2: Create silver transformation notebook
Task 3: Run notebook, verify silver tables
Task 4: Create gold aggregation tables
Task 5: Build semantic model measures
Task 6: Verify with sample DAX queries
```

Rules:
- Each task should be independently verifiable
- Complete and verify task N before starting task N+1
- If task N fails, don't start N+1
- Use the task list to track progress — it survives context compression

## Anti-Hallucination Rules

These are the most common hallucination triggers with Fabric MCP:

1. **Invented column names** — ALWAYS run `SELECT TOP 1 *` before writing queries. Never guess column names from table names.
2. **Assumed tool success** — Read every tool result. A 200 status doesn't mean the data is what you expected.
3. **Fabricated counts/stats** — If user asks "how many rows?", run `SELECT COUNT(*) FROM table`. Don't estimate.
4. **Made-up workspace/lakehouse names** — Use `list_workspaces`, `list_lakehouses`. Don't guess.
5. **Phantom tables** — After loading data, verify with `list_tables`. New tables take 5-10 min to appear in SQL endpoint.
6. **Repeated failed approaches** — If something fails twice the same way, try a different approach or ask the user. Don't loop.

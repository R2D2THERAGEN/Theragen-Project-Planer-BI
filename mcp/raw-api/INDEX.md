# raw_api_call — API Router

When using the `raw_api_call` tool, follow this 3-step lookup:

1. **Read this file** to pick the audience + category
2. **Read the audience _index.md** to find the exact operation
3. **Read the category .md** for endpoint, params, body, and examples

NEVER read more than one category file per call. NEVER read all files.

---

## Audiences & Base URLs

| Audience | Base URL | Token Scope |
|----------|----------|-------------|
| `fabric` | `https://api.fabric.microsoft.com` | `https://api.fabric.microsoft.com/.default` |
| `powerbi` | `https://api.powerbi.com` | `https://analysis.windows.net/powerbi/api/.default` |
| `graph` | `https://graph.microsoft.com` | `https://graph.microsoft.com/.default` |
| `storage` | `https://{account}.dfs.fabric.microsoft.com` | `https://storage.azure.com/.default` |

---

## Category Map

### fabric/ — Fabric REST API (v1)
→ Read `fabric/_index.md` for: workspaces, items, git, deployment-pipelines, connections, capacities, domains, jobs, lro, shortcuts, environments, lakehouses, warehouses, notebooks, semantic-models, reports, pipelines, eventhouses, eventstreams, kql, mirrored-databases, dataflows, spark-jobs, graphql-apis, copy-jobs, admin

### powerbi/ — Power BI REST API (v1.0)
→ Read `powerbi/_index.md` for: datasets, reports, dashboards, imports, refresh, export, gateways, apps, scorecards

### graph/ — Microsoft Graph API (v1.0)
→ Read `graph/_index.md` for: users, mail, teams, channels, drives, sites, calendar, groups

### storage/ — OneLake ADLS Gen2
→ Read `storage/_index.md` for: filesystem operations (ls, read, write, delete, mkdir)

---

## Common Patterns

**Pagination:** Fabric APIs return `continuationToken` in response. Pass as query param to get next page.

**Long Running Operations (LRO):** Some APIs return `202 Accepted` with headers:
- `Location` — poll this URL for status
- `x-ms-operation-id` — operation ID
- `Retry-After` — seconds to wait
Poll: `GET {Location}` until status is `Succeeded` or `Failed`.

**Item Types (case-sensitive):** `Lakehouse`, `Warehouse`, `Notebook`, `SemanticModel`, `Report`, `DataPipeline`, `Environment`, `Eventhouse`, `Eventstream`, `KQLDatabase`, `KQLQueryset`, `KQLDashboard`, `MLModel`, `MLExperiment`, `SparkJobDefinition`, `MirroredDatabase`, `GraphQLApi`, `CopyJob`, `Dataflow`, `Reflex`

**Error Shape:** All errors return `{ "errorCode": "...", "message": "..." }` in body.

# Power BI REST API — Category Index

Base: `https://api.powerbi.com/v1.0/myorg`
Audience: `powerbi`

Pick the category below, then read its .md file for full specs.

| Category | File | Key Operations |
|----------|------|----------------|
| Datasets (Semantic Models) | `powerbi/datasets.md` | Execute Queries (DAX), Refresh, Get Parameters, Bind, Take Over |
| Reports | `powerbi/reports.md` | Export To File (PDF/PPTX/PNG/XLSX), Clone, Rebind |
| Gateways | `powerbi/gateways.md` | List Gateways, Datasources |
| Apps | `powerbi/apps.md` | List, Get |
| Admin | `powerbi/admin.md` | Tenant-wide scans, activity events, capacity management |

## Common Patterns

Most Power BI v1.0 endpoints follow:
```
GET    /v1.0/myorg/groups/{groupId}/datasets          ← groupId = workspaceId
GET    /v1.0/myorg/groups/{groupId}/reports
POST   /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/executeQueries
```

Note: `groups/{groupId}` = workspace. The term "group" is legacy Power BI terminology for workspace.

## When to Use Power BI API vs Fabric API

- **DAX query execution** → Power BI API (`executeQueries`)
- **Dataset refresh** → Power BI API (`refreshes`)
- **Report export** → Power BI API (`exportTo`)
- **Item CRUD** → Fabric API (more complete)
- **Item definitions** → Fabric API (getDefinition/updateDefinition)
- **Git/CI/CD** → Fabric API

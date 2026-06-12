# Fabric REST API — Category Index

Base: `https://api.fabric.microsoft.com/v1`
Audience: `fabric`

Pick the category below, then read its .md file for full specs.

## Core Platform

| Category | File | Operations |
|----------|------|------------|
| Workspaces | `fabric/workspaces.md` | List, Create, Get, Update, Delete, Assign to Capacity/Domain, Role Assignments (CRUD) |
| Items (Generic) | `fabric/items.md` | List, Create, Get, Update, Delete, Get/Update Definition, Move, List Connections |
| Git Integration | `fabric/git.md` | Connect, Disconnect, Get Connection, Get Status, Commit, Update from Git, Initialize, Get/Update Credentials |
| Deployment Pipelines | `fabric/deployment-pipelines.md` | CRUD, Deploy Stage Content, List Stages/Items, Assign/Unassign Workspace, Role Assignments |
| Connections | `fabric/connections.md` | CRUD, Role Assignments (CRUD), List Supported Types |
| Capacities | `fabric/capacities.md` | List Capacities |
| Domains | `fabric/domains.md` | Get, List Domains |
| Job Scheduler | `fabric/jobs.md` | Run On Demand, Cancel, Create/Get/Update/Delete Schedule, List Instances/Schedules |
| Long Running Ops | `fabric/lro.md` | Get Operation State, Get Operation Result |
| OneLake Shortcuts | `fabric/shortcuts.md` | Create, Get, Delete, List, Bulk Create |
| OneLake Security | `fabric/onelake-security.md` | Create/Update/Get/Delete/List Data Access Roles |
| External Data Shares | `fabric/external-shares.md` | Create, Get, Delete, Revoke, List |
| Private Endpoints | `fabric/private-endpoints.md` | Create, Get, Delete, List |

## Workload Items

| Category | File | Key Operations |
|----------|------|----------------|
| Lakehouse | `fabric/lakehouse.md` | CRUD + Definition, List Tables, Load Table, Table Maintenance Jobs |
| Warehouse | `fabric/warehouse.md` | CRUD, Get Connection String |
| Notebook | `fabric/notebook.md` | CRUD + Definition |
| Semantic Model | `fabric/semantic-model.md` | CRUD + Definition |
| Report | `fabric/report.md` | CRUD + Definition |
| Data Pipeline | `fabric/pipeline.md` | CRUD + Definition |
| Environment | `fabric/environment.md` | CRUD + Definition, Publish, Cancel Publish |
| Eventhouse | `fabric/eventhouse.md` | CRUD + Definition |
| Eventstream | `fabric/eventstream.md` | CRUD + Definition, Topology (sources, destinations, pause/resume) |
| KQL Database | `fabric/kql-database.md` | CRUD + Definition |
| KQL Queryset | `fabric/kql-queryset.md` | CRUD + Definition |
| Mirrored Database | `fabric/mirrored-database.md` | CRUD + Definition, Start/Stop/Get Mirroring Status |
| Dataflow | `fabric/dataflow.md` | CRUD + Definition |
| Spark Job Definition | `fabric/spark-job.md` | CRUD + Definition |
| GraphQL API | `fabric/graphql-api.md` | CRUD + Definition |
| Copy Job | `fabric/copy-job.md` | CRUD + Definition |

## Admin (Tenant-Level)

| Category | File | Operations |
|----------|------|------------|
| Admin Domains | `fabric/admin-domains.md` | CRUD, Assign/Unassign Workspaces, Role Assignments |
| Admin Items | `fabric/admin-items.md` | Get Item, List Items, List Access Details |
| Admin Labels | `fabric/admin-labels.md` | Bulk Set/Remove Sensitivity Labels |
| Admin Tenants | `fabric/admin-tenants.md` | List/Update Tenant Settings, Capacity/Domain/Workspace Overrides |
| Admin Users | `fabric/admin-users.md` | List Access Entities |
| Admin Workspaces | `fabric/admin-workspaces.md` | Get, List All, Access Details, Restore, List Git Connections |

## Standard CRUD Pattern (most workload items)

Most workload items follow this pattern — only read the specific .md if you need item-specific fields:

```
List:    GET    /v1/workspaces/{workspaceId}/{itemTypePlural}
Create:  POST   /v1/workspaces/{workspaceId}/{itemTypePlural}
Get:     GET    /v1/workspaces/{workspaceId}/{itemTypePlural}/{itemId}
Update:  PATCH  /v1/workspaces/{workspaceId}/{itemTypePlural}/{itemId}
Delete:  DELETE /v1/workspaces/{workspaceId}/{itemTypePlural}/{itemId}
GetDef:  POST   /v1/workspaces/{workspaceId}/{itemTypePlural}/{itemId}/getDefinition
UpdateDef: POST /v1/workspaces/{workspaceId}/{itemTypePlural}/{itemId}/updateDefinition
```

Plural names: `lakehouses`, `warehouses`, `notebooks`, `semanticModels`, `reports`, `dataPipelines`, `environments`, `eventhouses`, `eventstreams`, `kqlDatabases`, `kqlQuerysets`, `mirroredDatabases`, `dataflows`, `sparkJobDefinitions`, `graphQLApis`, `copyJobs`

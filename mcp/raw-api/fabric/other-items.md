# Other Workload Items

Base: `https://api.fabric.microsoft.com/v1`

All follow the standard CRUD + Definition pattern described in `_index.md`.

## Dataflow
```
Plural: dataflows
List/Create/Get/Update/Delete + GetDef/UpdateDef
```

## Spark Job Definition
```
Plural: sparkJobDefinitions
List/Create/Get/Update/Delete + GetDef/UpdateDef
```

## GraphQL API
```
Plural: graphQLApis
List/Create/Get/Update/Delete + GetDef/UpdateDef
```

## Copy Job
```
Plural: copyJobs
List/Create/Get/Update/Delete + GetDef/UpdateDef
```

## Reflex (Activator)
```
Plural: reflexes
List/Create/Get/Update/Delete + GetDef/UpdateDef
```

## ML Model
```
Plural: mlModels
List/Create/Get/Update/Delete (no definition support)
```

## ML Experiment
```
Plural: mlExperiments
List/Create/Get/Update/Delete (no definition support)
```

## Paginated Report
```
Plural: paginatedReports
Update, List (limited operations)
```

## SQL Database
```
Plural: sqlDatabases
List/Create/Get/Update/Delete
```

## Dashboard (Legacy)
```
GET /v1/workspaces/{workspaceId}/dashboards  (list only, read-only)
```

## OneLake Data Access Security
```
POST   /v1/workspaces/{workspaceId}/items/{itemId}/dataAccessSecurity/roles
GET    /v1/workspaces/{workspaceId}/items/{itemId}/dataAccessSecurity/roles/{roleId}
PATCH  /v1/workspaces/{workspaceId}/items/{itemId}/dataAccessSecurity/roles/{roleId}
DELETE /v1/workspaces/{workspaceId}/items/{itemId}/dataAccessSecurity/roles/{roleId}
GET    /v1/workspaces/{workspaceId}/items/{itemId}/dataAccessSecurity/roles
POST   /v1/workspaces/{workspaceId}/items/{itemId}/dataAccessSecurity/roles/batch
```

## External Data Shares
```
POST   /v1/workspaces/{workspaceId}/items/{itemId}/externalDataShares
GET    /v1/workspaces/{workspaceId}/items/{itemId}/externalDataShares/{externalDataShareId}
DELETE /v1/workspaces/{workspaceId}/items/{itemId}/externalDataShares/{externalDataShareId}
POST   /v1/workspaces/{workspaceId}/items/{itemId}/externalDataShares/{externalDataShareId}/revoke
GET    /v1/workspaces/{workspaceId}/items/{itemId}/externalDataShares
```

## Managed Private Endpoints
```
POST   /v1/workspaces/{workspaceId}/managedPrivateEndpoints
GET    /v1/workspaces/{workspaceId}/managedPrivateEndpoints/{managedPrivateEndpointId}
DELETE /v1/workspaces/{workspaceId}/managedPrivateEndpoints/{managedPrivateEndpointId}
GET    /v1/workspaces/{workspaceId}/managedPrivateEndpoints
```

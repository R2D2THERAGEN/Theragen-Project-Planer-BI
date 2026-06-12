# Real-Time Intelligence APIs

Base: `https://api.fabric.microsoft.com/v1`

All follow standard CRUD + Definition pattern.

## Eventhouse
```
List:      GET    /v1/workspaces/{workspaceId}/eventhouses
Create:    POST   /v1/workspaces/{workspaceId}/eventhouses  (LRO)
Get:       GET    /v1/workspaces/{workspaceId}/eventhouses/{eventhouseId}
Update:    PATCH  /v1/workspaces/{workspaceId}/eventhouses/{eventhouseId}
Delete:    DELETE /v1/workspaces/{workspaceId}/eventhouses/{eventhouseId}
GetDef:    POST   /v1/workspaces/{workspaceId}/eventhouses/{eventhouseId}/getDefinition
UpdateDef: POST   /v1/workspaces/{workspaceId}/eventhouses/{eventhouseId}/updateDefinition
```

## KQL Database
```
List:      GET    /v1/workspaces/{workspaceId}/kqlDatabases
Create:    POST   /v1/workspaces/{workspaceId}/kqlDatabases  (LRO)
Get:       GET    /v1/workspaces/{workspaceId}/kqlDatabases/{kqlDatabaseId}
Update:    PATCH  /v1/workspaces/{workspaceId}/kqlDatabases/{kqlDatabaseId}
Delete:    DELETE /v1/workspaces/{workspaceId}/kqlDatabases/{kqlDatabaseId}
```
Create body: `{ "displayName": "logs_db", "creationPayload": { "databaseType": "ReadWrite", "parentEventhouseItemId": "uuid" } }`

## KQL Queryset
```
List/Create/Get/Update/Delete: /v1/workspaces/{workspaceId}/kqlQuerysets/{...}
GetDef/UpdateDef: same pattern
```

## KQL Dashboard
```
List/Create/Get/Update/Delete: /v1/workspaces/{workspaceId}/kqlDashboards/{...}
GetDef/UpdateDef: same pattern
```

## Eventstream
```
List:      GET    /v1/workspaces/{workspaceId}/eventstreams
Create:    POST   /v1/workspaces/{workspaceId}/eventstreams  (LRO)
Get:       GET    /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}
Update:    PATCH  /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}
Delete:    DELETE /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}
```

### Eventstream Topology Operations
```
GET  /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/topology
POST /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/pause
POST /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/resume
```

## Mirrored Database
```
List:    GET    /v1/workspaces/{workspaceId}/mirroredDatabases
Create:  POST   /v1/workspaces/{workspaceId}/mirroredDatabases  (LRO)
Get:     GET    /v1/workspaces/{workspaceId}/mirroredDatabases/{mirroredDatabaseId}
Update:  PATCH  /v1/workspaces/{workspaceId}/mirroredDatabases/{mirroredDatabaseId}
Delete:  DELETE /v1/workspaces/{workspaceId}/mirroredDatabases/{mirroredDatabaseId}
```

### Mirroring Control
```
POST /v1/workspaces/{workspaceId}/mirroredDatabases/{mirroredDatabaseId}/startMirroring
POST /v1/workspaces/{workspaceId}/mirroredDatabases/{mirroredDatabaseId}/stopMirroring
GET  /v1/workspaces/{workspaceId}/mirroredDatabases/{mirroredDatabaseId}/getMirroringStatus
GET  /v1/workspaces/{workspaceId}/mirroredDatabases/{mirroredDatabaseId}/getTablesMirroringStatus
```

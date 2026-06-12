# Report API

Base: `https://api.fabric.microsoft.com/v1`

## Standard CRUD
```
List:    GET    /v1/workspaces/{workspaceId}/reports
Create:  POST   /v1/workspaces/{workspaceId}/reports  (LRO)
Get:     GET    /v1/workspaces/{workspaceId}/reports/{reportId}
Update:  PATCH  /v1/workspaces/{workspaceId}/reports/{reportId}
Delete:  DELETE /v1/workspaces/{workspaceId}/reports/{reportId}
```

## Get Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/reports/{reportId}/getDefinition
POST /v1/workspaces/{workspaceId}/reports/{reportId}/getDefinition?format=PBIR
```
Format: `PBIR` returns the enhanced report format (folder structure with individual pages/visuals).
Default returns legacy PBIX-style definition.

## Update Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/reports/{reportId}/updateDefinition
```

## Permissions
- Scope: `Report.ReadWrite.All` or `Item.ReadWrite.All`
